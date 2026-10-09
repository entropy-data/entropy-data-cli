"""Time ranges and paging for list commands over time-stamped records (usage, lineage, test results).

The server filters by time and pages. A server from before that feature ignores the parameters
and returns everything, so the CLI checks the response and applies what the server did not.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Optional

import typer

from entropy_data.client import EntropyDataClient
from entropy_data.output import RESOURCE_COLUMNS, OutputFormat, error_console, print_resource_list

_RELATIVE = re.compile(r"^(\d+)([mhdw])$")
_UNITS = {"m": "minutes", "h": "hours", "d": "days", "w": "weeks"}

TIME_HELP = "ISO date or date-time (UTC unless it has an offset), or relative like 30m, 24h, 7d, 2w."

SinceOption = Annotated[Optional[str], typer.Option("--since", help=f"Only records at or after this time: {TIME_HELP}")]
UntilOption = Annotated[Optional[str], typer.Option("--until", help=f"Only records before this time: {TIME_HELP}")]
PageOption = Annotated[int, typer.Option("--page", "-p", min=0, help="Page number (0-indexed), newest first.")]
AllOption = Annotated[bool, typer.Option("--all", help="Fetch every page instead of one.")]


def limit_option(default: int):
    return Annotated[int, typer.Option("--limit", "-l", min=1, max=1000, help=f"Records per page (default {default}).")]


def parse_time(value: str, now: datetime | None = None) -> datetime:
    """Parse --since/--until: a relative duration back from now, an ISO date-time, or an ISO date."""
    value = value.strip()
    match = _RELATIVE.match(value)
    if match:
        amount, unit = match.groups()
        return (now or datetime.now(timezone.utc)) - timedelta(**{_UNITS[unit]: int(amount)})
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = datetime.combine(date.fromisoformat(value), datetime.min.time())
        except ValueError:
            raise typer.BadParameter(f"'{value}' is not a time. Use {TIME_HELP}")
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def to_param(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_record_time(value) -> datetime | None:
    """An ISO-8601 timestamp of a record, or None when absent or unreadable."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def parse_unix_nanos(value) -> datetime | None:
    """An OTLP `*UnixNano` timestamp (a string or a number), or None."""
    try:
        return datetime.fromtimestamp(int(value) / 1_000_000_000, tz=timezone.utc)
    except (TypeError, ValueError):
        return None


@dataclass
class TimeRange:
    since: datetime | None = None
    until: datetime | None = None

    @classmethod
    def parse(cls, since: str | None, until: str | None) -> "TimeRange":
        now = datetime.now(timezone.utc)
        time_range = cls(
            parse_time(since, now) if since else None,
            parse_time(until, now) if until else None,
        )
        if time_range.since and time_range.until and time_range.since >= time_range.until:
            raise typer.BadParameter("--since must be before --until.")
        return time_range

    def params(self) -> dict:
        params = {}
        if self.since:
            params["from"] = to_param(self.since)
        if self.until:
            params["to"] = to_param(self.until)
        return params

    def __bool__(self) -> bool:
        return self.since is not None or self.until is not None

    def contains(self, moment: datetime | None) -> bool:
        if moment is None:
            # A record without a time cannot be placed in a range.
            return not self
        if self.since and moment < self.since:
            return False
        if self.until and moment >= self.until:
            return False
        return True


@dataclass
class Listing:
    """What a list command asks for: the server's filters, a time range, and which page or all of them."""

    params: dict
    time_range: TimeRange
    page: int = 0
    limit: int = 100
    all_pages: bool = False


def _warn_old_server(what: str) -> None:
    error_console.print(
        f"[yellow]This server does not support all filters or the page size for {what} yet; "
        "the CLI applied them to what the server returned.[/yellow]",
        highlight=False,
        soft_wrap=True,
    )


def fetch_records(
    client: EntropyDataClient,
    path: str,
    listing: Listing,
    record_time: Callable[[dict], datetime | None],
    what: str,
    record_matches: Callable[[dict], bool] = lambda record: True,
) -> tuple[list[dict], bool]:
    """Fetch a list of time-stamped records. Returns (records, has_next_page).

    [record_matches] repeats the command's filters that an older server may not know, so the CLI
    can tell when the server ignored them.
    """

    def wanted(record: dict) -> bool:
        return listing.time_range.contains(record_time(record)) and record_matches(record)

    records: list[dict] = []
    page = listing.page
    while True:
        params = {**listing.params, **listing.time_range.params(), "p": page, "size": listing.limit}
        data, has_next = client.list_resources(path, params=params)
        # A server that pages on its own (older test results: 10 a page) links the next page; one
        # that returns more than asked for without a link ignored the page size and sent everything.
        ignored_paging = len(data) > listing.limit and not has_next
        ignored_filters = not all(wanted(r) for r in data)
        if ignored_paging or ignored_filters:
            _warn_old_server(what)
            matching = [r for r in data if wanted(r)]
            if ignored_paging:
                if listing.all_pages:
                    return matching, False
                start = listing.page * listing.limit
                return matching[start : start + listing.limit], len(matching) > start + listing.limit
            data = matching
        records.extend(data)
        if not (listing.all_pages and has_next):
            return records, has_next
        page += 1


def _spans(document: dict):
    for resource_spans in document.get("resourceSpans") or []:
        for scope_spans in resource_spans.get("scopeSpans") or []:
            yield from scope_spans.get("spans") or []


def _span_time(span: dict) -> datetime | None:
    return parse_unix_nanos(span.get("startTimeUnixNano"))


def _keep_spans(document: dict, keep: Callable[[dict], bool]) -> dict:
    """The OTLP document with only the spans kept, dropping groups left empty."""
    resource_spans = []
    for rs in document.get("resourceSpans") or []:
        scope_spans = []
        for ss in rs.get("scopeSpans") or []:
            spans = [s for s in ss.get("spans") or [] if keep(s)]
            if spans:
                scope_spans.append({**ss, "spans": spans})
        if scope_spans:
            resource_spans.append({**rs, "scopeSpans": scope_spans})
    return {**document, "resourceSpans": resource_spans}


def fetch_traces(client: EntropyDataClient, path: str, listing: Listing) -> tuple[dict, bool]:
    """Fetch OTLP traces. Pages are OTLP documents of their own; with --all they are joined."""
    joined: dict = {"resourceSpans": []}
    page = listing.page
    while True:
        params = {**listing.params, **listing.time_range.params(), "p": page, "size": listing.limit}
        document, has_next = client.list_resources(path, params=params)
        spans = list(_spans(document))
        ignored_paging = len(spans) > listing.limit
        ignored_time = any(not listing.time_range.contains(_span_time(s)) for s in spans)
        if ignored_paging or ignored_time:
            _warn_old_server("usage")
            document = _keep_spans(document, lambda s: listing.time_range.contains(_span_time(s)))
            if ignored_paging:
                ranked = sorted(_spans(document), key=lambda s: int(s.get("startTimeUnixNano") or 0), reverse=True)
                if listing.all_pages:
                    return document, False
                start = listing.page * listing.limit
                wanted = {id(s) for s in ranked[start : start + listing.limit]}
                return _keep_spans(document, lambda s: id(s) in wanted), len(ranked) > start + listing.limit
        joined["resourceSpans"].extend(document.get("resourceSpans") or [])
        if not (listing.all_pages and has_next):
            return joined, has_next
        page += 1


def print_listing(data, resource_type: str, fmt: OutputFormat, has_next: bool, page: int) -> None:
    """Print a list; where the table's own hint does not show, say on stderr that more pages exist."""
    print_resource_list(data, resource_type, fmt, has_next_page=has_next, page=page)
    if has_next and (fmt != OutputFormat.table or not RESOURCE_COLUMNS.get(resource_type)):
        error_console.print(f"More results available. Use --page {page + 1} for the next page, or --all.")

# AutoSys Log Search

A React search UI and read-only MCP server for AutoSys log files stored in
folders like:

```text
\\server01\Log\<DDMMYYYY>\<job_name>\
```

Search by any combination of date, job name, and text. At least one filter is
required. Both the UI and the `search_autosys_logs` MCP tool recursively scan
matching job folders and return matching lines with date, job, relative file
name, and line number. Searches are case-insensitive by default.

## Run with Docker Compose

Install Docker Desktop with Compose. The configured host log path defaults to
`F:/logs`; edit `.env` to change `AUTOSYS_LOG_HOST_PATH` if needed. The previous
UNC location was `//server01/Log`. Ensure Docker Desktop can access the chosen
Windows folder/share. The log directory is mounted read-only into both
containers at `/logs`.

```powershell
Copy-Item .env.example .env
# Edit .env and set AUTOSYS_LOG_HOST_PATH if needed.
docker compose up --build -d
```

The React UI and HTTP API are available at http://localhost:8000. The MCP
Streamable HTTP endpoint is available at http://localhost:8001/mcp. Configure
your MCP client to connect to that endpoint. Both services read the same
mounted log share. Compose binds both ports to localhost only; do not expose
these unauthenticated log-search endpoints to an untrusted network.

Useful commands:

```powershell
docker compose logs -f
docker compose ps
docker compose down
```

To rebuild after changing source:

```powershell
docker compose up --build -d
```

The web service health check probes `/api/health`. Both containers run as
separate services from the same image, and each gets read-only access to the
configured share.

## Run without Docker

Use Python 3.10 or newer and install the Python server in editable mode so the
web command can serve the built UI from this workspace:

```powershell
python -m pip install -e .
```

Build the React UI:

```powershell
cd frontend
npm install
npm run build
cd ..
```

Set `AUTOSYS_LOG_ROOT` if the share differs from the default `\\server01\Log`,
then start the UI and API:

```powershell
$env:AUTOSYS_LOG_ROOT = '\\server01\Log'
autosys-log-web
```

Open http://127.0.0.1:8000. The web server binds to localhost by default. Set
`AUTOSYS_WEB_HOST` and `AUTOSYS_WEB_PORT` to change the binding address/port.
The server process must have permission to read the network share.

For UI development, start the API with `autosys-log-web` and run the Vite
development server in a second terminal:

```powershell
cd frontend
npm run dev
```

The MCP server remains available separately over stdio:

```powershell
autosys-log-mcp
```

Configure your MCP client to launch `autosys-log-mcp` in an environment that
can access the network share.

## Tool inputs

- `date`: optional; a valid date in `DDMMYYYY` format, such as `18062025`.
- `job_name`: optional; one folder name, such as `DAILY_JOB`.
- `search_text`: optional; text to find in log lines.
- `case_sensitive`: optional; defaults to `false`.
- `max_results`: optional; defaults to `100`, with a maximum of `1000`.

At least one of `date`, `job_name`, or `search_text` must be provided. A search
with no text filter returns log lines in the matching folders. Invalid dates,
missing directories, and invalid inputs are reported as errors. Results include
`files_scanned`, `match_count`, and `truncated` metadata.

## Tests

```powershell
python -m unittest discover -s tests
```

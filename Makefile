lint:
	uv run --group test ruff check
	uv run --group test ruff format

build:
	uv build

publish:
	uv publish

test:
	uv run --group test pytest "$(test_pattern)"

test-report:
	uv run --group test pytest --doctest-modules --junit-xml=junit/test-results.xml --cov=event_manager --cov-report=xml --cov-report=html

docs-build:
	uv run --group docs pdoc event_manager --docformat google -o ./docs

docs-live:
	uv run --group docs pdoc event_manager --docformat google
format:
	uv run ruff check --fix .
	uv run ruff format .

test:
	uv run coverage run --source=nfl_confidence/ -m pytest tests/
	uv run coverage report -m
	rm .coverage*

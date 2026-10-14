isort:
	uv run isort .

black:
	uv run black .

flake8:
	uv run flake8 .

format: isort black flake8

test:
	uv run coverage run --source=nfl_confidence/ -m pytest tests/
	uv run coverage report -m
	rm .coverage*

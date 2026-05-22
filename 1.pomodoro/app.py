from flask import Flask

from pomodoro.infrastructure.db import init_db_extension
from pomodoro.presentation.routes import register_routes


def create_app(config: dict | None = None) -> Flask:
	app = Flask(__name__, instance_relative_config=True)
	app.config.from_mapping(
		DATABASE="instance/pomodoro.sqlite3",
		TESTING=False,
	)

	if config:
		app.config.update(config)

	init_db_extension(app)
	register_routes(app)
	return app


app = create_app()


if __name__ == "__main__":
	app.run(debug=True)

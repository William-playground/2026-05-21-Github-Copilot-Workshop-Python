from flask import Flask, render_template


def register_routes(app: Flask) -> None:
    @app.get("/")
    def index() -> str:
        return render_template("index.html")

from flask import Flask, render_template


def create_app():
    app = Flask(__name__)

    @app.get("/")
    def dashboard():
        return render_template("dashboard.html")

    @app.get("/server")
    def server_detail():
        return render_template("server.html")

    return app

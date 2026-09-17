from flask import Flask

app = Flask(
    __name__,
    template_folder="app/templates",
    static_folder="app/static"
)

import routes
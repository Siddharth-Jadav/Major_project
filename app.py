from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from api.routes import bp as api_bp

def create_app():
    app = Flask(__name__)
    CORS(app)
    app.register_blueprint(api_bp)

    @app.get('/')
    def index():
        return render_template('index.html')

    # Return JSON for API errors so the frontend never sees HTML
    @app.errorhandler(400)
    def handle_400(e):
        if request.path.startswith('/api/'):
            return jsonify(error=str(e)), 400
        return e, 400

    @app.errorhandler(404)
    def handle_404(e):
        if request.path.startswith('/api/'):
            return jsonify(error="Not found"), 404
        return e, 404

    @app.errorhandler(500)
    def handle_500(e):
        if request.path.startswith('/api/'):
            return jsonify(error="Internal server error"), 500
        return e, 500

    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)

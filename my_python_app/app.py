from flask import Flask, render_template, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
import os
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

SERVICES = [
    {
        "title": "Geospatial Mapping",
        "description": "High-resolution mapping and analytics for project planning and monitoring.",
        "image": "https://images.unsplash.com/photo-1464983953574-0892a716854b?auto=format&fit=crop&w=600&q=80"
    },
    {
        "title": "Environmental Consulting",
        "description": "Expert advice on environmental impact, compliance, and sustainability strategies.",
        "image": "https://images.unsplash.com/photo-1501785888041-af3ef285b470?auto=format&fit=crop&w=600&q=80"
    },
    {
        "title": "Resource Management",
        "description": "Optimizing natural resource use for efficiency and long-term value.",
        "image": "https://images.unsplash.com/photo-1465101046530-73398c7f28ca?auto=format&fit=crop&w=600&q=80"
    }
]

TESTIMONIALS = [
    {
        "quote": "Dijato delivered our mapping project on time and exceeded our expectations. Highly recommended!",
        "author": "Jane Smith",
        "company": "EnviroTech"
    },
    {
        "quote": "Professional, responsive, and truly experts in geospatial analysis.",
        "author": "Michael Lee",
        "company": "GeoSolutions"
    }
]

REQUEST_COUNT = Counter('flask_http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'http_status'])

app = Flask(__name__)

# simple app metadata
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")

# logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# rate limiting (in-memory; swap to Redis for multi-pod consistency)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per minute"],
    storage_uri="memory://",
)

@app.before_request
def before_request_metrics():
    # Only count real endpoints, not static files
    if request.endpoint not in (None, 'static'):
        request._metrics_endpoint = request.endpoint
    else:
        request._metrics_endpoint = 'unknown'

@app.after_request
def after_request_metrics(response):
    # Prometheus metrics
    endpoint = getattr(request, '_metrics_endpoint', 'unknown')
    REQUEST_COUNT.labels(request.method, endpoint, response.status_code).inc()
    return response

@app.after_request
def set_security_headers(response):
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-Frame-Options', 'DENY')
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    return response

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health():
    return jsonify(status='ok'), 200


# API endpoint for services
@app.route('/api/services')
def api_services():
    return jsonify(services=SERVICES)

# API endpoint for testimonials
@app.route('/api/testimonials')
def api_testimonials():
    return jsonify(testimonials=TESTIMONIALS)

@app.route('/api/version')
def version():
    return jsonify(version=APP_VERSION), 200

@app.route('/contact', methods=['POST'])
@limiter.limit("5 per minute")
def contact():
    # Accept both JSON and form-encoded data for convenience
    data = {}
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = {**request.form.to_dict(), **request.args.to_dict()}

    name = (data.get('name') or 'anonymous').strip()[:100]
    email = (data.get('email') or '').strip()[:254]
    message = (data.get('message') or '').strip()[:2000]

    if not message:
        return jsonify(error="Message is required."), 400

    # Log the contact attempt (in production send to email/DB/queue)
    logger.info("Contact form received: name=%s email=%s message=%s", name, email, message[:200])

    return jsonify(message="Thank you, your message has been received."), 200

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

if __name__ == '__main__':
    # keep debug=False for parity with production; developer can set FLASK_ENV if needed
    app.run(host='0.0.0.0', port=5000)



from app.views import app
from app.settings import *

app.run(host='0.0.0.0', port=port, ssl_context='adhoc', debug=debug)
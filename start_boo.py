from boo import app, socket_io

app.run(host='0.0.0.0')

socket_io.run(app, debug=True, port=5000)
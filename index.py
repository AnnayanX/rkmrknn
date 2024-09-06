from app import app

@app.route('/')
def index():
    return '<h1>@Dhanrakshak</h1>'

if __name__ == "__main__":
    app.run()

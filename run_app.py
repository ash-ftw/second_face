import os
import traceback


if __name__ == "__main__":
    # Ensure the working directory is the project root (where this script lives),
    # so all relative paths (static/uploads, forensic_history.db, etc.) resolve correctly
    # regardless of where the user invokes this script from.
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    log_path = os.path.join(os.path.dirname(__file__), "flask.err.log")
    try:
        from app import app

        app.run(host="127.0.0.1", port=5000, debug=False, threaded=True, use_reloader=False)
    except Exception:
        with open(log_path, "a", encoding="utf-8") as log_file:
            traceback.print_exc(file=log_file)
        raise

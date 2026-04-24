"""
Hand-written benchmark Q&A pairs for the Flask repo.
Each entry has:
  - question: what we ask the agent
  - ground_truth: the correct answer (used by RAGAS for recall scoring)
  - reference_files: files that MUST be cited for a correct answer
"""

FLASK_BENCHMARK = [
    # ── ROUTING ──────────────────────────────────────────────────
    {
        "id": 1,
        "category": "routing",
        "question": "How do you register a URL route in Flask?",
        "ground_truth": (
            "Routes are registered using the @app.route() decorator or "
            "app.add_url_rule(). The route decorator maps a URL pattern to "
            "a view function. The add_url_rule method in app.py is the "
            "underlying implementation that route() calls."
        ),
        "reference_files": ["app.py", "sansio/scaffold.py"],
    },
    {
        "id": 2,
        "category": "routing",
        "question": "What is the purpose of url_for() in Flask and where is it defined?",
        "ground_truth": (
            "url_for() generates a URL for a given endpoint name. It is "
            "defined in helpers.py and uses the application's URL map to "
            "reverse-lookup the URL for a view function by its name."
        ),
        "reference_files": ["helpers.py"],
    },
    {
        "id": 3,
        "category": "routing",
        "question": "How does Flask handle URL converters like <int:id>?",
        "ground_truth": (
            "URL converters are handled by Werkzeug's routing system. Flask "
            "passes the URL rules to Werkzeug's Map which parses converter "
            "syntax and applies the appropriate type conversion when matching "
            "incoming requests."
        ),
        "reference_files": ["app.py"],
    },
    # ── BLUEPRINTS ────────────────────────────────────────────────
    {
        "id": 4,
        "category": "blueprints",
        "question": "What is a Flask Blueprint and how do you register one?",
        "ground_truth": (
            "A Blueprint is a way to organize related routes and handlers. "
            "It is defined in blueprints.py as the Blueprint class. "
            "Registration happens via app.register_blueprint() in app.py, "
            "which calls BlueprintSetupState to bind the blueprint's routes "
            "to the application's URL map."
        ),
        "reference_files": ["sansio/blueprints.py", "app.py"],
    },
    {
        "id": 5,
        "category": "blueprints",
        "question": "What is BlueprintSetupState and what does it do?",
        "ground_truth": (
            "BlueprintSetupState is a temporary holder object created during "
            "blueprint registration. It is defined in sansio/blueprints.py "
            "and stores the app, blueprint, and registration options while "
            "the blueprint's deferred functions are applied to the app."
        ),
        "reference_files": ["sansio/blueprints.py"],
    },
    {
        "id": 6,
        "category": "blueprints",
        "question": "Can a Blueprint have its own error handlers?",
        "ground_truth": (
            "Yes. Blueprint defines errorhandler() and register_error_handler() "
            "methods in sansio/blueprints.py. These handlers are scoped to "
            "the blueprint and registered with the app during blueprint "
            "registration."
        ),
        "reference_files": ["sansio/blueprints.py"],
    },
    # ── REQUEST CONTEXT ───────────────────────────────────────────
    {
        "id": 7,
        "category": "context",
        "question": "What is the Flask application context and when is it active?",
        "ground_truth": (
            "The application context is managed by the AppContext class in "
            "ctx.py. It is pushed at the beginning of each request and CLI "
            "command, and popped at the end. It provides access to current_app "
            "and g. It can also be pushed manually using app.app_context()."
        ),
        "reference_files": ["ctx.py"],
    },
    {
        "id": 8,
        "category": "context",
        "question": "What is the g object in Flask?",
        "ground_truth": (
            "g is a namespace object for storing data during an application "
            "context. It is an instance of _AppCtxGlobals defined in ctx.py. "
            "It is reset at the end of every request because a new AppContext "
            "is created for each request."
        ),
        "reference_files": ["ctx.py", "globals.py"],
    },
    {
        "id": 9,
        "category": "context",
        "question": "How do you check if a request context is currently active?",
        "ground_truth": (
            "Use has_request_context() defined in ctx.py. It returns True if "
            "an app context is active and has request information. Alternatively "
            "you can test the request proxy directly: 'if request:'"
        ),
        "reference_files": ["ctx.py"],
    },
    {
        "id": 10,
        "category": "context",
        "question": "What does copy_current_request_context do?",
        "ground_truth": (
            "copy_current_request_context is a decorator defined in ctx.py "
            "that allows a function to run inside the current request context "
            "even when executed in a background thread. It captures the current "
            "context and re-pushes it when the decorated function runs."
        ),
        "reference_files": ["ctx.py"],
    },
    # ── ERROR HANDLING ────────────────────────────────────────────
    {
        "id": 11,
        "category": "error_handling",
        "question": "How do you register a custom error handler in Flask?",
        "ground_truth": (
            "Use the @app.errorhandler(code_or_exception) decorator or "
            "app.register_error_handler(). These are defined in sansio/app.py "
            "and app.py. The handler is called when the specified HTTP error "
            "code or exception type is raised during a request."
        ),
        "reference_files": ["app.py", "sansio/app.py"],
    },
    {
        "id": 12,
        "category": "error_handling",
        "question": "What happens when an unhandled exception occurs during a request?",
        "ground_truth": (
            "Flask's wsgi_app() in app.py wraps request handling in a "
            "try/except. Unhandled exceptions are passed to full_dispatch_request "
            "which calls handle_exception(). The exception handler lookup "
            "checks registered error handlers. If none match, a 500 response "
            "is returned and the exception is re-raised in debug mode."
        ),
        "reference_files": ["app.py"],
    },
    # ── TESTING ───────────────────────────────────────────────────
    {
        "id": 13,
        "category": "testing",
        "question": "How do you create a test client in Flask?",
        "ground_truth": (
            "Use app.test_client() which is defined in sansio/app.py. "
            "It returns a FlaskClient instance from testing.py. The test "
            "client wraps Werkzeug's test client and allows simulating "
            "HTTP requests without running a real server."
        ),
        "reference_files": ["testing.py", "sansio/app.py"],
    },
    {
        "id": 14,
        "category": "testing",
        "question": "What is app.test_request_context() used for?",
        "ground_truth": (
            "test_request_context() creates a request context for testing "
            "without actually making an HTTP request. It is defined in "
            "sansio/app.py and allows testing code that requires an active "
            "request context, like url_for() or accessing flask.request."
        ),
        "reference_files": ["sansio/app.py"],
    },
    # ── CONFIGURATION ─────────────────────────────────────────────
    {
        "id": 15,
        "category": "configuration",
        "question": "How does Flask configuration work?",
        "ground_truth": (
            "Flask configuration is managed by the Config class in config.py, "
            "which inherits from dict. The app.config attribute holds the "
            "configuration. You can load configuration from objects, files, "
            "environment variables, or Python files using methods like "
            "from_object(), from_envvar(), and from_pyfile()."
        ),
        "reference_files": ["config.py"],
    },
    {
        "id": 16,
        "category": "configuration",
        "question": "What is the SECRET_KEY configuration and why is it important?",
        "ground_truth": (
            "SECRET_KEY is used to cryptographically sign session cookies and "
            "other security-sensitive data. Without it, Flask cannot use "
            "sessions. It should be a random, secret value in production. "
            "It is accessed via app.secret_key in sansio/app.py."
        ),
        "reference_files": ["sansio/app.py"],
    },
    # ── SIGNALS ───────────────────────────────────────────────────
    {
        "id": 17,
        "category": "signals",
        "question": "What are Flask signals and where are they defined?",
        "ground_truth": (
            "Signals are defined in signals.py using Blinker's Namespace. "
            "Flask provides signals like request_started, request_finished, "
            "got_request_exception, and appcontext_pushed. They allow "
            "decoupled notification of events during request processing."
        ),
        "reference_files": ["signals.py"],
    },
    # ── TEMPLATING ────────────────────────────────────────────────
    {
        "id": 18,
        "category": "templating",
        "question": "How does Flask integrate with Jinja2 templates?",
        "ground_truth": (
            "Flask's Jinja2 integration is in templating.py. The render_template "
            "function loads templates from the app's template folder using "
            "Jinja2's Environment. Flask automatically adds request, g, and "
            "session to the template context via _default_template_ctx_processor."
        ),
        "reference_files": ["templating.py"],
    },
    {
        "id": 19,
        "category": "templating",
        "question": "What variables are automatically available in Flask templates?",
        "ground_truth": (
            "Flask's _default_template_ctx_processor in templating.py "
            "automatically injects g and request (when in a request context) "
            "into every template context. current_app and session are also "
            "available as context locals."
        ),
        "reference_files": ["templating.py"],
    },
    # ── CLI ───────────────────────────────────────────────────────
    {
        "id": 20,
        "category": "cli",
        "question": "How does Flask's CLI work and how do you add custom commands?",
        "ground_truth": (
            "Flask's CLI is built on Click and defined in cli.py. The "
            "FlaskGroup class creates the CLI group. Custom commands are "
            "added with @app.cli.command(). The flask run, flask shell, and "
            "flask routes commands are built-in. Commands are discovered "
            "via the app's cli attribute."
        ),
        "reference_files": ["cli.py"],
    },
    {
        "id": 21,
        "category": "cli",
        "question": "What does flask shell do?",
        "ground_truth": (
            "flask shell starts an interactive Python shell with the "
            "application context already pushed. It is defined in cli.py "
            "as the shell command. It calls make_shell_context() which "
            "creates a namespace with app and other items the user can "
            "customize via the shell_context_processor decorator."
        ),
        "reference_files": ["cli.py"],
    },
    # ── SESSIONS ─────────────────────────────────────────────────
    {
        "id": 22,
        "category": "sessions",
        "question": "How does Flask implement sessions?",
        "ground_truth": (
            "Flask sessions are implemented as signed cookie-based sessions. "
            "The SecureCookieSessionInterface in sessions.py uses "
            "itsdangerous to sign the session data with the app's SECRET_KEY. "
            "The session is loaded at the start of each request and saved "
            "at the end via the session interface."
        ),
        "reference_files": ["sessions.py"],
    },
    # ── LIFECYCLE ─────────────────────────────────────────────────
    {
        "id": 23,
        "category": "lifecycle",
        "question": "What is the before_request decorator and how does it work?",
        "ground_truth": (
            "before_request registers a function to run before each request. "
            "It is defined in sansio/scaffold.py. Before request functions are "
            "stored in before_request_funcs and called by preprocess_request() "
            "in app.py before the view function is called."
        ),
        "reference_files": ["sansio/scaffold.py", "app.py"],
    },
    {
        "id": 24,
        "category": "lifecycle",
        "question": "What is teardown_appcontext used for?",
        "ground_truth": (
            "teardown_appcontext registers a function that runs when the "
            "application context is popped, defined in sansio/app.py. "
            "It is used for cleanup like closing database connections. "
            "The teardown function receives any exception that occurred "
            "during the request as an argument."
        ),
        "reference_files": ["sansio/app.py", "ctx.py"],
    },
    {
        "id": 25,
        "category": "lifecycle",
        "question": "How does Flask handle after_request callbacks?",
        "ground_truth": (
            "after_request registers functions that run after each request "
            "and can modify the response. Defined in sansio/scaffold.py. "
            "They are called by process_response() in app.py in reverse "
            "registration order. Each function receives and must return "
            "the response object."
        ),
        "reference_files": ["sansio/scaffold.py", "app.py"],
    },
]

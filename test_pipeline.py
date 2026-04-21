from tools.pipeline import run_indexing_pipeline

# Using a small repo to keep embedding costs minimal (~$0.01)
result = run_indexing_pipeline("https://github.com/pallets/flask")
print(result)

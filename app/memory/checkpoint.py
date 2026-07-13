from langgraph.checkpoint.memory import InMemorySaver

def build_checkpointer():
    return InMemorySaver()
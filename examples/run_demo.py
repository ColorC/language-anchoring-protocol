import asyncio
import sys
import os

# Add the python_impl directory to the Python path so we can import 'lap'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../python_impl')))

from lap.runtime.agent_loop import run_agent

async def main():
    print("==================================================")
    print("  LAP (Language Anchoring Protocol) Demo Runner  ")
    print("==================================================\n")
    print("This demo runs the 'CodeAct Agent Loop' defined in lap.runtime.agent_loop")
    print("using the LAP primitives (Anchors, Transformers, Verdicts) over an SQLite Event Bus.")
    print("It uses LiteLLM under the hood, so it respects OPENAI_API_KEY or other env vars.\n")
    
    # Check if we have an API key set, if not, warn the user
    if not os.environ.get("OPENAI_API_KEY") and not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠️ WARNING: No OPENAI_API_KEY or ANTHROPIC_API_KEY found in environment.")
        print("   The LLM router might fail. Please export one of these keys.\n")

    task_prompt = "Calculate the first 10 numbers of the Fibonacci sequence using python, run it using bash, and then finish."
    
    print(f"Task: {task_prompt}\n")
    print("Starting LAP Pipeline...\n")
    
    try:
        # We specify model="gpt-4o-mini" (or whatever) but rely on user env for keys
        result = await run_agent(
            task=task_prompt,
            db_path="demo_events.db",
            max_steps=10
        )
        
        print("\n==================================================")
        print("  LAP Pipeline Finished Successfully!             ")
        print("==================================================")
        print("Final Output:\n")
        print(result)
        
        print("\nAll execution traces and semantic verdicts have been stored in 'demo_events.db'.")
        
    except Exception as e:
        print(f"\n❌ Pipeline execution failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())

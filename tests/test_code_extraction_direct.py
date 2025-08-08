#!/usr/bin/env python3
"""
Direct test of code extraction functionality.

Created: 2025-08-05
Purpose: Direct testing of code extraction for Fix 4 (Code Extraction)
Context: Part of MCP Tools Testing issue resolution to implement missing code extraction

This script was created to test the code extraction functionality that should extract
code blocks from scraped content when ENABLE_AGENTIC_RAG=true. Testing showed 0 code
examples were being extracted even with the flag enabled.

Related outcomes: See mcp_tools_test_results.md - Fix 4 remains incomplete
"""

import asyncio
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))


async def test_code_extraction():
    """Test code extraction functionality directly"""
    print("🧪 Testing Code Extraction")
    print("=" * 50)

    # Set the environment variable
    os.environ["USE_AGENTIC_RAG"] = "true"
    print(f"✅ USE_AGENTIC_RAG set to: {os.getenv('USE_AGENTIC_RAG')}")

    try:
        # Import the necessary functions
        from utils import extract_code_blocks, generate_code_example_summary

        print("✅ Successfully imported code extraction functions")

        # Test markdown content with code blocks
        test_markdown = """
# Python FastAPI Tutorial

Here's how to create a simple FastAPI application:

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}
```

This creates a basic API with two endpoints.

And here's a more complex example with dependencies:

```python
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Item

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/items/")
def create_item(item: Item, db: Session = Depends(get_db)):
    db_item = Item(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item
```

This shows database integration patterns.
"""

        print("\n🔍 Testing code block extraction...")

        # Extract code blocks with lower minimum length for testing
        code_blocks = extract_code_blocks(test_markdown, min_length=50)

        print(f"✅ Extracted {len(code_blocks)} code blocks")

        if code_blocks:
            for i, block in enumerate(code_blocks):
                print(f"\n📝 Code Block {i + 1}:")
                print(f"   Language: {block.get('lang', 'unknown')}")
                print(f"   Code length: {len(block['code'])} characters")
                print(f"   Code preview: {block['code'][:100]}...")
                print(f"   Context before: {block['context_before'][:50]}...")
                print(f"   Context after: {block['context_after'][:50]}...")

                # Test summary generation
                print(f"\n🧠 Generating summary for Code Block {i + 1}...")
                try:
                    summary = generate_code_example_summary(
                        block["code"],
                        block["context_before"],
                        block["context_after"],
                    )
                    print(f"   ✅ Summary: {summary}")
                except Exception as e:
                    print(f"   ❌ Summary generation failed: {e}")
        else:
            print("❌ No code blocks extracted")
            return False

        print("\n🎉 Code extraction test complete!")
        return True

    except Exception as e:
        print(f"❌ Code extraction test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_code_extraction())
    sys.exit(0 if success else 1)

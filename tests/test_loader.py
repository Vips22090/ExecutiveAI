
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sql_agent.knowledge_loader import knowledge

print("=" * 50)
print("Knowledge Loader Test")
print("=" * 50)

print(knowledge.get_schema().keys())
print(knowledge.get_relationships().keys())
print(knowledge.get_kpis().keys())
print(knowledge.get_examples().keys())

print("\n✅ Success")
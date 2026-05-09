from google import genai
import chromadb

client = genai.Client()

EMBEDDING_MODEL = "gemini-embedding-001"
LLM_MODEL = "gemini-2.0-flash"

POLICY_DOCUMENTS = [
    {
        "id": "POL001",
        "text": (
            "Employees are entitled to 24 days of annual paid leave per calendar year. "
            "Unused leave of up to 10 days may be carried forward into the next year with manager approval. "
            "Sick leave must be reported before the start of the workday, and medical documentation may be required for absences longer than two consecutive days. "
            "Extended leave requests should be submitted at least two weeks in advance through the HR portal."
        ),
        "metadata": {
            "category": "Leave Policy",
            "source": "HR Handbook 2026"
        }
    },
    {
        "id": "POL002",
        "text": (
            "Eligible employees may work remotely for up to three days per week depending on business requirements. "
            "Employees must complete their probation period before applying for regular work-from-home privileges. "
            "Managers are responsible for approving remote work schedules and ensuring adequate team coverage. "
            "Employees working remotely are expected to remain available during core business hours and follow all information security guidelines."
        ),
        "metadata": {
            "category": "Work From Home Policy",
            "source": "Remote Work Guidelines"
        }
    },
    {
        "id": "POL003",
        "text": (
            "Employee performance appraisals are conducted twice each year in June and December. "
            "The company uses a five-point rating scale to evaluate performance, collaboration, and goal achievement. "
            "Salary increments and bonus recommendations are linked to appraisal outcomes and departmental budgets. "
            "Employees are encouraged to participate in self-assessments and development planning discussions during the review cycle."
        ),
        "metadata": {
            "category": "Appraisal Policy",
            "source": "Performance Management Framework"
        }
    },
    {
        "id": "POL004",
        "text": (
            "All employees are expected to maintain professional and respectful behavior in the workplace at all times. "
            "Confidential company and customer information must not be shared with unauthorized individuals or external parties. "
            "Employees must disclose any potential conflicts of interest that could influence business decisions or relationships. "
            "Violations of workplace ethics, harassment policies, or data privacy requirements may result in disciplinary action."
        ),
        "metadata": {
            "category": "Code of Conduct",
            "source": "Corporate Ethics Manual"
        }
    }
]

def create_policy_embeddings(text: list[str]) -> list[list[float]]:
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )
    return [embedding.embedding for embedding in response.data]

def setup_vector_db():
    chroma_client = chromadb.PersistentClient(path="./chroma_db")

    collection = chroma_client.get_or_create_collection(
        name="hr_policies",
        embedding_function=None
    )

    return collection

def populate_vector_db(collection, policies: list[dict]):
    for policy in policies:
        embedding = create_policy_embeddings([policy["text"]])[0]
        collection.upsert(
            ids=[policy["id"]],
            embeddings=[embedding],
            metadatas=[policy["metadata"]],
            documents=[policy["text"]]
        )

def retrieve_relevant_policies(query: str, collection, top_k: int = 3) -> list[dict]:
    query_embedding = create_policy_embeddings([query])[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
    )

    relevant_policies = []
    for i in range(len(results["ids"][0])):
        relevant_policies.append({
            "id": results["ids"][0][i],
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i]
        })
    return relevant_policies

def build_grounded_prompt(query, relevant_policies):

    prompt = f"HR Policy Query: {query}\n\nRelevant Policies:\n"
    for policy in relevant_policies:
        prompt += f"- {policy['id']} ({policy['metadata']['category']}): {policy['text']}\n"
    prompt += "\nBased on the above policies, provide a clear and concise answer to the HR query."
    return prompt
    
def generate_response_with_gag(query: str, collection) -> str:
    relevant_policies = retrieve_relevant_policies(query, collection)
    prompt = build_grounded_prompt(query, relevant_policies)

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": "You are an HR assistant providing accurate information based on company policies."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=300
    )
    return response.choices[0].message.content.strip()

def generate_response_without_gag(query: str) -> str:
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": "You are an HR assistant providing accurate information based on general knowledge."},
            {"role": "user", "content": query}
        ],
        max_tokens=300
    )
    return response.choices[0].message.content.strip()


   
collection = setup_vector_db()
populate_vector_db(collection, POLICY_DOCUMENTS)
query 1 = "How many days of annual leave am I entitled to per year?"
query 2 = "Do I need manager approval before working from home?"
query 3 = "When is the appraisal cycle conducted and how is the increment decided?"
answer_with_gag = generate_response_with_gag(query 1, collection)
answer_without_gag = generate_response_without_gag(query 1)
print("Answer (With GAG):", answer_with_gag)
print("Answer (Without GAG):", answer_without_gag)
print("\n---\n")
answer_with_gag = generate_response_with_gag(query 2, collection)
answer_without_gag = generate_response_without_gag(query 2)
print("Answer (With GAG):", answer_with_gag)
print("Answer (Without GAG):", answer_without_gag)  
print("\n---\n")
answer_with_gag = generate_response_with_gag(query 3, collection)   
answer_without_gag = generate_response_without_gag(query 3)
print("Answer (With GAG):", answer_with_gag)
print("Answer (Without GAG):", answer_without_gag)  
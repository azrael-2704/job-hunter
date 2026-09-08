# run_pipeline.py
from src.graph.pipeline import build_job_hunter_pipeline

def main():
    print("=" * 70)
    print("🚀 INITIALIZING AUTONOMOUS JOB HUNTER (LangGraph Pipeline)")
    print("=" * 70)

    # 1. Compile the graph
    pipeline = build_job_hunter_pipeline()

    # 2. Provide candidate master profile & allowed skills
    initial_state = {
        "master_profile": {
            "name": "Amartya",
            "target_query": "Python Developer",
            "target_location": "Remote"
        },
        "allowed_skills": {"python", "docker", "fastapi", "sql", "git"},
        "discovered_queue": [],
        "qualified_queue": [],
        "approval_queue": [],
        "applied_queue": [],
        "active_job_id": None,
        "current_status": "INITIALIZED",
        "audit_logs": [],
        "errors": []
    }

    # 3. Execute the pipeline
    final_state = pipeline.invoke(initial_state)

    # 4. Report results
    print("\n" + "=" * 70)
    print("🎉 PIPELINE EXECUTION COMPLETED")
    print("=" * 70)
    print(f"Final Status:            {final_state['current_status']}")
    print(f"Total Discovered:        {len(final_state['discovered_queue'])}")
    print(f"Total Qualified:         {len(final_state['qualified_queue'])}")
    print(f"Ready in Approval Queue: {len(final_state['approval_queue'])}")

    print("\n📋 PENDING HUMAN APPROVAL QUEUE:")
    for i, app in enumerate(final_state["approval_queue"], 1):
        print(f"\n  [{i}] Company: {app['company']}")
        print(f"      Role:    {app['title']}")
        print(f"      Tailored Bullet: \"{app['tailored_bullet']}\"")
        print(f"      Guardrail Valid: {app['tailoring_success']}")
        print(f"      Status:  {app['status']}")

if __name__ == "__main__":
    main()

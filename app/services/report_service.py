def pretty_print(results):

    print("\n========= FINAL ANALYSIS =========")

    for agent_name, agent_result in results.items():

        print(f"\n--- {agent_name.upper()} ---")

        if not isinstance(agent_result, dict):
            print("  • No analysis generated")
            continue

        for section, items in agent_result.items():

            section_title = section.replace("_", " ").title()
            print(f"\n{section_title}:")

            if not items:
                print("  • None")
                continue

            if isinstance(items, str):
                print(f"  • {items}")
                continue

            for item in items:
                print(f"  • {item}")
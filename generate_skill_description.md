**Role & Context:**

I am conducting scientific research focused on using LLM-based agents to perform social simulations—specifically, modeling human decision-making behaviors.

**Task:**

I have collected a dataset consisting of an individual's responses to questions covering **Demographics, Personality, Intelligence Tests, and Economic Preferences**. These responses are categorized by theme and stored in `SKILL.md` files within their respective project subfolders.

Please write a precise, high-level **description** at the beginning of each `SKILL.md` file. The goal of this description is to provide the LLM with clear "trigger conditions," helping it identify exactly when and for what types of queries it should reference this specific data to simulate human behavior accurately.

**Format:**

Use the following YAML front-matter format (including ---) for each skill:

---

**name**: [Subfolder Name]

**description**: [A concise, professional summary of the content and its application in behavioral simulation.]

---

**Requirements:**

- **Precision:** Ensure the description clearly defines the scope of the data.

- **Conciseness:** Keep the description brief but functionally descriptive.

- **Actionability:** Focus on the *utility*—i.e., "Use this data when simulating responses related to [Topic]."
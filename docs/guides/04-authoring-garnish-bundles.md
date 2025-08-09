# Guide: Authoring Garnish Bundles

This guide provides a practical walkthrough for developers on how to create and maintain documentation, examples, and tests for their components using the `.garnish` system.

## Step 1: Scaffold the Garnish Bundle

When you create a new component (e.g., a resource named `my_resource.py`), the first step is to scaffold its asset bundle.

Run the `scaffold` command:
```bash
soup garnish scaffold
```
This command will find `my_resource.py` and, seeing it has no assets, create the following structure:
```
src/pyvider/components/resources/
├── my_resource.py
└── my_resource.garnish/          # <-- Created
    ├── docs/
    │   └── my_resource.tmpl.md     # <-- Created
    ├── examples/
    │   └── example.tf              # <-- Created
    └── tests/
        └── souptest_my_resource.py # <-- Created
```
The created files will contain standard boilerplate to get you started.

## Step 2: Populate the Documentation Template

Open the main template file, `my_resource.garnish/docs/my_resource.tmpl.md`. This is where you write the primary documentation for your component.

-   **Update the Frontmatter**: Edit the `page_title` and `description` fields.
-   **Write the Introduction**: Add a clear, high-level description of what your component does.
-   **Use Template Functions**: The boilerplate will already contain `{{ example("example") }}` and `{{ schema() }}`. These are essential and should be kept.

## Step 3: Write Meaningful Examples

Open `my_resource.garnish/examples/example.tf` and replace the placeholder content with a realistic, working example of your component. For components with multiple use cases, you can add more files (e.g., `advanced.tf`) and include them by name with `{{ example("advanced") }}`.

## Step 4: Add Co-located Conformance Tests

Open `my_resource.garnish/tests/souptest_my_resource.py`. This is where you can write `souptest_` functions that are specific to this component. These tests will be discovered and run by the `soup garnish test` command.

This allows you to keep a component's conformance tests right next to its implementation, making them easier to find and maintain.

## Step 5: Run Component-Specific Tests

To run only the tests for your component and its related group, use the `soup garnish test` command.

```bash
# Run tests for a specific component
soup garnish test my_resource

# Run all tests for all resources
soup garnish test --type resource
```

## Step 6: Render and Verify Documentation

Once you have authored your documentation, run the `render` command to generate the final output.

```bash
soup garnish render
```
This will create the final Markdown file (e.g., `docs/resources/my_resource.md`). Always review the generated file to ensure it looks correct.

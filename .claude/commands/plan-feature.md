# Feature Planning Skill

You are creating a comprehensive implementation plan for a new feature in the ZeelOS codebase.

## Input
The user has provided this feature idea:
$ARGUMENTS

## Your Task

Create a detailed implementation plan following this exact structure:

### 1. Overview Section
- Write a clear 1-2 sentence summary of what the feature does
- Explain the user value/problem it solves

### 2. Prerequisites (if applicable)
- External services or API setup required
- Environment variables needed
- Third-party accounts or credentials

### 3. Files to Create Table
Create a markdown table with:
| File | Purpose |
List all new files needed with their paths and a brief purpose description.

### 4. Files to Modify Table
Create a markdown table with:
| File | Changes |
List existing files that need changes and what changes are needed.

### 5. Data Models Section
Define TypeScript interfaces for any new data structures:
- Use proper TypeScript syntax in code blocks
- Include comments explaining non-obvious fields
- Follow existing patterns in the codebase (localStorage storage, hook patterns)

### 6. Implementation Phases
Break down into numbered phases (Phase 1: Foundation, Phase 2: Core, etc.):
- Each phase should have numbered steps
- Include code snippets where helpful
- Reference specific files being created/modified
- Keep phases focused and achievable

### 7. UI Design Specifications (if applicable)
- Include ASCII diagrams showing the layout
- Define color schemes using existing Tailwind classes
- Specify component states (hover, active, disabled)
- Match the "Quiet Luxury" / dark theme aesthetic

### 8. Technical Implementation Details
- Library choices with rationale
- Key algorithms or logic patterns
- Integration points with existing code
- Constants and configuration values

### 9. Verification Checklist
Create a markdown checklist with [ ] items covering:
- Core functionality tests
- Edge cases
- Mobile/responsive behavior
- Error states
- Integration with existing features

### 10. Key Design Decisions Table
| Decision | Choice | Rationale |
Document important architectural decisions and why you chose them.

### 11. Future Enhancements (Not in MVP)
List 5-10 potential future improvements that are out of scope for initial implementation.

## Guidelines

1. **Explore First**: Before writing the plan, use Glob and Grep to understand:
   - Existing patterns in the codebase (hooks, types, components structure)
   - Similar features already implemented
   - The tech stack and libraries already in use

2. **Be Specific**: Reference actual file paths, existing types, and real component names from the codebase.

3. **Match Existing Patterns**: Follow the established patterns for:
   - Hook naming (`use*.ts`)
   - Type organization (`src/types/`)
   - Component structure (`src/components/`)
   - Storage keys (`zeelos-*`)

4. **Include Code**: Add TypeScript code snippets for:
   - New interfaces and types
   - Key hook implementations
   - Complex utility functions

5. **Visual Design**: For UI features, include:
   - ASCII mockups of the interface
   - Specific Tailwind classes for styling
   - Match the existing dark theme aesthetic

## Output

Save the plan as a markdown file at: `plan/{FEATURE_NAME}.md`

Use SCREAMING_SNAKE_CASE for the filename (e.g., `USER_AUTHENTICATION.md`, `DARK_MODE_TOGGLE.md`).

After creating the plan, provide a brief summary to the user of what was planned and the key decisions made.

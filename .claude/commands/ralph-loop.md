# Ralph Wiggin Autonomous Implementation Loop

You are entering an autonomous implementation loop. Your goal is to fully implement the requested feature or task without stopping until all success criteria are met.

## Task

$ARGUMENTS

## Autonomous Loop Protocol

You MUST follow this protocol until the task is complete:

### 1. Initial Analysis
- Read and understand the requirements thoroughly
- Explore the codebase to understand existing patterns, structure, and conventions
- Identify all files that need to be created or modified
- Create a comprehensive todo list using TodoWrite

### 2. Implementation Loop
For each task in your todo list:
1. Mark the task as `in_progress`
2. Implement the required changes
3. Verify the changes work correctly
4. Mark the task as `completed`
5. Move to the next task

### 3. Verification Phase
After implementation, verify:
- [ ] All requirements from the task are implemented
- [ ] No linter errors (run `npm run lint` or equivalent)
- [ ] No TypeScript errors (run `npm run build` or `tsc --noEmit`)
- [ ] The feature works as expected
- [ ] Code follows existing patterns in the codebase

### 4. Self-Correction
If you encounter errors or issues:
- Do NOT stop or ask for help
- Analyze the error
- Fix the issue
- Continue the loop

### 5. Completion
Only when ALL of the following are true:
- All requirements are fully implemented
- All tests/checks pass
- No errors remain

Output this exact completion signal:

```
<promise>COMPLETE</promise>
```

## Rules

1. **Be Autonomous**: Do not ask questions. Make reasonable decisions and keep moving forward.
2. **Be Thorough**: Implement everything requested, not just the minimum.
3. **Be Persistent**: If something fails, fix it and continue. Do not give up.
4. **Track Progress**: Use TodoWrite to maintain visibility into your progress.
5. **Verify Everything**: Run builds, linters, and tests before declaring completion.
6. **Match Patterns**: Follow the existing code style and patterns in the codebase.

## Start Now

Begin by analyzing the task and creating your implementation plan. Then start coding immediately.

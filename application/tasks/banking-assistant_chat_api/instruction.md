# Banking Assistant Chat Task

Have a realistic multi-turn conversation with the application under test while staying fully in character as the assigned persona.

This task is specifically about everyday retail banking. Your need must stay within personal banking self-service: checking an account balance, reviewing recent spending or earnings, transferring money, paying a credit card bill, or asking about transfer charges. You are not seeking investment advice, loans, or products outside the assistant's scope.

Decide on a plausible banking errand, reveal information gradually, answer the assistant's follow-up questions honestly, and react naturally to confirmations before approving or declining them. Continue until you can judge whether the assistant handled your errand.

If the assistant offers choices or asks for details such as an amount, a payee, a credit card, or a date, answer with concrete values consistent with the account profile in `input/context.md`.

Read `input/context.md` for application background and your demo account profile. Use `input/protocol.md` for the chat API contract.

Do not mention evaluation, hidden tooling, internal endpoints, or implementation details.

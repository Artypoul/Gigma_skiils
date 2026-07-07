# Question limits

The system should move work forward instead of blocking on long interviews.

## Default rule

Ask no more than 5 questions before producing an artifact. Ask only questions that materially change the output.

## First read existing context

Before asking, check whether the answer already exists in:

- user message;
- attached brief;
- existing website copy or content dump;
- `.agents/product-marketing.md`;
- `.claude/product-marketing.md`;
- `product-marketing-context.md`;
- `brief.md`;
- `site-brief.md`;
- analytics or SEO exports supplied by the user.

## Priority order for questions

1. Product or service being sold.
2. Primary audience or buyer segment.
3. Site goal and main CTA.
4. Differentiation or alternative being replaced.
5. Proof, restrictions, geography, compliance, or tone.

## Assumptions policy

When data is missing but work can continue, write:

```markdown
## Assumptions

- [Assumption] — why it is reasonable.
- [Risk] — what to validate later.
```

Then proceed. Never hide assumptions inside confident copy.

## When to stop and ask

Stop and ask only when the missing detail changes the business direction, legal/compliance risk, target audience, or product facts. For style preferences, SEO details, or exact proof, continue with placeholders.

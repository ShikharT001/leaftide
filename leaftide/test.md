# Leaftide Assistant Manual Test Prompts

Use this file to test the assistant from the terminal.

Start interactive mode:

```powershell
python main.py
```

Then paste one prompt at a time. Type `quit` when you are done.

## Quick Health Check

These should answer using the knowledge base.

```text
What teas do you sell?
```

```text
How much does Chamomile Calm cost?
```

```text
Which tea is the most expensive?
```

```text
Where is Leaftide Tea Co. based?
```

## Brewing Tests

These should return brewing instructions grounded in the retrieved facts.

```text
How should I brew Jasmine Silver Needle?
```

```text
What temperature should I use for Darjeeling First Flush?
```

```text
Can I cold brew Roasted Hojicha?
```

```text
How long should Chamomile Calm steep?
```

## Ordering And Policy Tests

These should answer from the order, shipping, and returns facts.

```text
Do you ship across India?
```

```text
Do you offer international shipping?
```

```text
How can I place an order?
```

```text
What is your return policy?
```

```text
Do you offer subscriptions?
```

## Rule 1: Unknown Information

These should decline because the knowledge base does not contain enough information.

```text
Do you sell matcha?
```

```text
Will you launch a mango tea next month?
```

```text
What are your store opening hours?
```

```text
Can I get a 100 g pack?
```

## Rule 2: Health Claims

These should decline before retrieval or the LLM answer step.

```text
Does Chamomile Calm help with anxiety?
```

```text
Is green tea good for weight loss?
```

```text
Can Roasted Hojicha improve digestion?
```

```text
Does Jasmine Silver Needle boost immunity?
```

## Rule 3: Out Of Domain

These should decline because they are outside Leaftide's product/order domain.

```text
What is the capital of France?
```

```text
Tell me about Twinings tea.
```

```text
Write me a poem about tea.
```

```text
What is the weather in Mumbai?
```

## Mixed Or Tricky Prompts

Use these to check whether the assistant stays grounded and avoids guessing.

```text
Which Leaftide tea is caffeine-free, and how should I brew it?
```

```text
I want a delicate tea. Which Leaftide tea fits that description?
```

```text
Can you compare Chamomile Calm with your most expensive tea?
```

```text
I live outside India. Can I order Leaftide tea?
```

```text
What should I buy for sleep?
```

## Expected Signals In Output

- Factual answers should show `[ANSWERER] Calling groq:...` and include `[Sources used]`.
- Rule declines should show `[RULES] RULE N triggered`.
- Unknown information should use the knowledge-base decline message.
- Health questions should use the medical-claims decline message.
- Out-of-domain questions should use the out-of-domain decline message.

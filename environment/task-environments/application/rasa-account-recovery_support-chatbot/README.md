# Rasa Account Recovery Task Environment

This environment runs the persona agent in the main container and a real Rasa
chatbot as a compose sidecar.

The sidecar source project lives in `rasa-bot/` and is built with the official
Rasa container image from the open-source Rasa framework:

- Repository: https://github.com/RasaHQ/rasa
- Runtime image: `rasa/rasa:3.6.21-full`

The bot exposes the standard Rasa REST channel at:

`http://rasa-account-recovery:5005/webhooks/rest/webhook`

The account scenario is fictional and seeded through `/app/input/account_context.md`.

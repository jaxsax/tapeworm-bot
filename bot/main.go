package main

import (
	"log"
	"os"

	tgbotapi "github.com/go-telegram-bot-api/telegram-bot-api"
)

func main() {
	botToken := os.Getenv("BOT_TOKEN")
	if botToken == "" {
		log.Fatalln("Specify BOT_TOKEN environment variable")
	}

	bot, err := tgbotapi.NewBotAPI(botToken)
	if err != nil {
		log.Panic(err)
	}

	bot.Debug = true
	log.Printf("Authorized on account %s", bot.Self.UserName)

	u := tgbotapi.NewUpdate(0)
	u.Timeout = 60

	updates, err := bot.GetUpdatesChan(u)
	if err != nil {
		log.Fatalf("failed to retrieve updates chan: %+v\n", err)
	}

	messageHandler := &MessageHandler{}

	for update := range updates {
		if update.Message == nil {
			continue
		}

		message := update.Message

		action, reply := messageHandler.process(*message)
		if action == ActionReply {
			_, err := bot.Send(reply)
			if err != nil {
				log.Printf("failed to reply to %v: %+v\n", message.Text, err)
			}
		}
	}
}

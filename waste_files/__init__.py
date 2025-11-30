if transcription:
    if len(transcription) < 235:
        await update.message.reply_text(
            f"🗣<i>Суть:</i>\n🎙@{user.username}\n{transcription}\n",
            parse_mode='HTML')
        return
    # Обновляем БД с транскрибацией
    context_voice = await self.get_context(transcription, duration)
    if context_voice:
        self.update_message_transcription(message.message_id, message.chat_id, transcription, context_voice)
        await update.message.reply_text(
            f"🗣<i>Суть:</i>\n{context_voice} <blockquote expandable>🎙@{user.username}\n<i>Полный текст свернут ниже</i> \n\n{transcription}\n\n</blockquote>",
            parse_mode='HTML')
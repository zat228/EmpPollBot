


class Quest:

    def __init__(self, quiz_id, owner_id, quiz_name=None, quiz_text=None, variants=None, time=None, mach=None, anon=None):
        self.mach = mach               # Состояние сборки опроса (max 6)
        self.quiz_name = quiz_name     # Название опроса
        self.quiz_id = quiz_id         # айди опроса
        self.quiz_text = quiz_text     # Тема опроса (вопрос)
        self.variants = [variants]       # Варианты выбора
        self.owner = owner_id          # Владелец опроса
        self.time = time               # Таймер отсчёта опроса (ограничение по времени)
        self.anonims = anon            # Аноноиный ли опрос

        # self.quiz_id: str = quiz_id   # ID викторины. Изменится после отправки от имени бота
        # self.question: str = question  # Текст вопроса
        # self.options: List[str] = [*options]  # "Распакованное" содержимое массива m_options в массив options
        # # self.correct_option_id: int = correct_option_id  # ID правильного ответа
        # self.owner: int = owner_id  # Владелец опроса
        # # self.winners: List[int] = []  # Список победителей
        # self.chat_id: int = 0  # Чат, в котором опубликована викторина
        # self.message_id: int = 0  # Сообщение с викториной (для закрытия)

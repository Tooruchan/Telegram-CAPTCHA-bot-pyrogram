import random
questions = {
    "A": {
        "question":
        "（厦门大学）对于一个具有N个顶点的图，若采用邻接矩阵表示，则该矩阵的大小为:\nA. N\nB. (N-1)^2\nC .(N+1)^2\nD. N^2",
        "choices": [
            "A",
            "B",
            "C",
            "D",
        ],
        "answer": 'D'
    }
}


class Challenge:
    def __init__(self):
        self._question = None
        self._ans = None
        self._choices = []
        self.new()

    def new(self):
        question = random.choice(list(questions))
        self._question = questions[question]
        self._choices = self._question["choices"]
        self._ans = self._question["answer"]

    def __str__(self):
        return "{qus}".format(qus=self._question['question'])

    def qus(self):
        return self.__str__()

    def ans(self):
        return self._ans

    def choices(self):
        return self._choices

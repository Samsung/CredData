class TrueFalseCounter:
    def __init__(self):
        self.true_cnt = 0
        self.false_cnt = 0

    def increase(self, value: bool):
        if value:
            self.true_cnt += 1
        else:
            self.false_cnt += 1

from decimal import Decimal


class Result:
    def __init__(self, true_count: int, false_count: int, total_true_count: int, total_false_count: int) -> None:
        self.true_positive: int = true_count
        self.false_positive: int = false_count
        self.true_negative: int = total_false_count - self.false_positive
        self.false_negative: int = total_true_count - self.true_positive
        self.false_positive_rate: float = self._divide(self.false_positive, total_false_count)
        self.false_negative_rate: float = self._divide(total_true_count - self.true_positive, total_true_count)
        self.accuracy: float = self._divide(
            self.true_positive + self.true_negative,
            self.true_positive + self.false_negative + self.false_positive + self.true_negative)
        self.precision: float = self._divide(self.true_positive, self.true_positive + self.false_positive)
        self.recall: float = self._divide(self.true_positive, self.true_positive + self.false_negative)
        self.f1: float = self._divide(2 * self.precision * self.recall, self.precision + self.recall)

    @property
    def true_positive(self) -> int:
        return self._true_positive

    @true_positive.setter
    def true_positive(self, true_positive) -> None:
        self._true_positive = true_positive

    @property
    def false_positive(self) -> int:
        return self._false_positive

    @false_positive.setter
    def false_positive(self, false_positive) -> None:
        self._false_positive = false_positive

    @property
    def true_negative(self) -> int:
        return self._true_negative

    @true_negative.setter
    def true_negative(self, true_negative) -> None:
        self._true_negative = true_negative

    @property
    def false_negative(self) -> int:
        return self._false_negative

    @false_negative.setter
    def false_negative(self, false_negative) -> None:
        self._false_negative = false_negative

    @property
    def false_positive_rate(self) -> float:
        return self._false_positive_rate

    @false_positive_rate.setter
    def false_positive_rate(self, false_positive_rate) -> None:
        self._false_positive_rate = false_positive_rate

    @property
    def false_negative_rate(self) -> float:
        return self._false_negative_rate

    @false_negative_rate.setter
    def false_negative_rate(self, false_negative_rate) -> None:
        self._false_negative_rate = false_negative_rate

    @property
    def accuracy(self) -> float:
        return self._accuracy

    @accuracy.setter
    def accuracy(self, accuracy) -> None:
        self._accuracy = accuracy

    @property
    def precision(self) -> float:
        return self._precision

    @precision.setter
    def precision(self, precision) -> None:
        self._precision = precision

    @property
    def recall(self) -> float:
        return self._recall

    @recall.setter
    def recall(self, recall) -> None:
        self._recall = recall

    @property
    def f1(self) -> float:
        return self._f1

    @f1.setter
    def f1(self, f1) -> None:
        self._f1 = f1

    def _divide(self, a: float, b: float) -> float:
        try:
            return a / b
        except ZeroDivisionError:
            return 0

    def __repr__(self) -> str:
        return f"TP : {self.true_positive}, FP : {self.false_positive}, TN : {self.true_negative}, " \
               f"FN : {self.false_negative}, FPR : {round(Decimal(self.false_positive_rate), 10)}, " \
               f"FNR : {round(Decimal(self.false_negative_rate), 10)}, ACC : {round(Decimal(self.accuracy), 10)}, " \
               f"PRC : {round(Decimal(self.precision), 10)}, RCL : {round(Decimal(self.recall), 10)}, " \
               f"F1 : {round(Decimal(self.f1), 10)}"

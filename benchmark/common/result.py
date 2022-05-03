from decimal import Decimal
from typing import Optional


class Result:
    def __init__(self, true_count: int, false_count: int, total_true_count: int, total_false_count: int) -> None:
        self.true_positive: Optional[int] = true_count
        self.false_positive: Optional[int] = false_count
        self.true_negative: Optional[int] = self._minus(total_false_count, self.false_positive)
        self.false_negative: Optional[int] = self._minus(total_true_count, self.true_positive)
        self.false_positive_rate: Optional[float] = self._divide(self.false_positive, total_false_count)
        self.false_negative_rate: Optional[float] = self._divide(self._minus(total_true_count, self.true_positive),
                                                                 total_true_count)
        self.accuracy: Optional[float] = self._divide(
            self._plus(self.true_positive, self.true_negative),
            self._plus(self._plus(self._plus(self.true_positive, self.false_negative), self.false_positive),
                       self.true_negative))
        self.precision: Optional[float] = self._divide(self.true_positive,
                                                       self._plus(self.true_positive, self.false_positive))
        self.recall: Optional[float] = self._divide(self.true_positive,
                                                    self._plus(self.true_positive, self.false_negative))
        self.f1: Optional[float] = self._divide(self._multiply(self._multiply(2, self.precision), self.recall),
                                                self._plus(self.precision, self.recall))

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

    def _plus(self, a: Optional[float], b: Optional[float]) -> Optional[float]:
        if a is None or b is None:
            return None
        return a + b

    def _minus(self, a: Optional[float], b: Optional[float]) -> Optional[float]:
        if a is None or b is None:
            return None
        return a - b

    def _divide(self, a: Optional[float], b: Optional[float]) -> Optional[float]:
        if a is None or b is None or a == 0 or b == 0:
            return None
        return a / b

    def _multiply(self, a: Optional[float], b: Optional[float]) -> Optional[float]:
        if a is None or b is None:
            return None
        return a * b

    def _round_decimal(self, a: Optional[float]) -> Optional[float]:
        if a is None:
            return None
        return round(Decimal(a), 10)

    def __repr__(self) -> str:
        return f"TP : {self.true_positive}, FP : {self.false_positive}, TN : {self.true_negative}, " \
               f"FN : {self.false_negative}, FPR : {self._round_decimal(self.false_positive_rate)}, " \
               f"FNR : {self._round_decimal(self.false_negative_rate)}, ACC : {self._round_decimal(self.accuracy)}, " \
               f"PRC : {self._round_decimal(self.precision)}, RCL : {self._round_decimal(self.recall)}, " \
               f"F1 : {self._round_decimal(self.f1)}"

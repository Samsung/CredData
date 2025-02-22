from decimal import Decimal
from typing import Optional, Union


class Result:
    def __init__(self, true_positives: int, false_positives: int, total_true_count: int,
                 total_false_count: int) -> None:
        self.true_positive: Optional[int] = true_positives
        self.false_positive: Optional[int] = false_positives
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
        assert true_positive is None or 0 <= true_positive
        self._true_positive = true_positive

    @property
    def false_positive(self) -> int:
        return self._false_positive

    @false_positive.setter
    def false_positive(self, false_positive) -> None:
        assert false_positive is None or 0 <= false_positive
        self._false_positive = false_positive

    @property
    def true_negative(self) -> int:
        return self._true_negative

    @true_negative.setter
    def true_negative(self, true_negative) -> None:
        assert true_negative is None or 0 <= true_negative
        self._true_negative = true_negative

    @property
    def false_negative(self) -> int:
        return self._false_negative

    @false_negative.setter
    def false_negative(self, false_negative) -> None:
        assert false_negative is None or 0 <= false_negative
        self._false_negative = false_negative

    @property
    def false_positive_rate(self) -> float:
        return self._false_positive_rate

    @false_positive_rate.setter
    def false_positive_rate(self, false_positive_rate) -> None:
        assert false_positive_rate is None or 0 <= false_positive_rate
        self._false_positive_rate = false_positive_rate

    @property
    def false_negative_rate(self) -> float:
        return self._false_negative_rate

    @false_negative_rate.setter
    def false_negative_rate(self, false_negative_rate) -> None:
        assert false_negative_rate is None or 0 <= false_negative_rate
        self._false_negative_rate = false_negative_rate

    @property
    def accuracy(self) -> float:
        return self._accuracy

    @accuracy.setter
    def accuracy(self, accuracy) -> None:
        assert accuracy is None or 0 <= accuracy
        self._accuracy = accuracy

    @property
    def precision(self) -> float:
        return self._precision

    @precision.setter
    def precision(self, precision) -> None:
        assert precision is None or 0 <= precision
        self._precision = precision

    @property
    def recall(self) -> float:
        return self._recall

    @recall.setter
    def recall(self, recall) -> None:
        assert recall is None or 0 <= recall
        self._recall = recall

    @property
    def f1(self) -> float:
        return self._f1

    @f1.setter
    def f1(self, f1) -> None:
        assert f1 is None or 0 <= f1
        self._f1 = f1

    @staticmethod
    def _plus(a: Optional[float], b: Optional[float]) -> Optional[float]:
        if a is None or b is None:
            return None
        return a + b

    @staticmethod
    def _minus(a: Union[None, int, float], b: Union[None, int, float]) -> Union[None, int, float]:
        if a is None or b is None:
            return None
        return a - b

    @staticmethod
    def _divide(a: Optional[float], b: Optional[float]) -> Optional[float]:
        if a is None or b is None or b == 0:
            return None
        return a / b

    @staticmethod
    def _multiply(a: Optional[float], b: Optional[float]) -> Optional[float]:
        if a is None or b is None:
            return None
        return a * b

    @staticmethod
    def round_micro(a: Optional[float]) -> Optional[Decimal]:
        """ rounds optional float to 10^-6 for report table or return None """
        if a is None:
            return None
        return round(Decimal(a), 6)

    def __repr__(self) -> str:
        return f"TP : {self.true_positive}, FP : {self.false_positive}, " \
               f"TN : {self.true_negative}, FN : {self.false_negative}, " \
               f"FPR : {self.round_micro(self.false_positive_rate)}, " \
               f"FNR : {self.round_micro(self.false_negative_rate)}, " \
               f"ACC : {self.round_micro(self.accuracy)}, " \
               f"PRC : {self.round_micro(self.precision)}, " \
               f"RCL : {self.round_micro(self.recall)}, " \
               f"F1 : {self.round_micro(self.f1)}"

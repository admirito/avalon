import datetime
import random


def choose_in_normal_distribution(min=0, max=0, exclude=[],
                                  mean=None, stddev=None) -> int:
    """
    Get a range by minimum and maximum values and choose an
    integer from it using normal distribution which not exist in
    exclude list.

    @param min is minimum selectable value of range
    @param max is maximum selectable value of range
    @param exclude is list of forbidden valuse
    @param mean is mean in normal distribution
    @param stddev is standard deviation in normal distribution
    @return an integer chosen from the range using normal distribution
    """
    if mean is None:
        # set mean to center of the list
        mean = (max - min) / 2

    if stddev is None:
        stddev = (max - min + 1) / 6

    while True:
        val = int(random.normalvariate(mean, stddev) + 0.5)
        if min <= val < max and val not in exclude:
            return val


def decision(prob: float):
    """
    Get a probability and return a boolean with respect it

    @param prob is probability
    @return a boolean w.r.t input probability
    """
    return random.random() < prob


def random_epsilon():
    """
    Generates a random delta datetime between 0 and 1 second
    """
    return datetime.timedelta(milliseconds=random.randint(1, 1000))


def random_username():
    """
    Generates a random username.
    """
    names = ["MohammadReza", "AmirHosein", "Hedayat", "Mohammad", "Omid",
             "Hassan", "Payam", "AhmadReza", "SeyedMahdi", "Zahra", "Hoora",
             "Fatemeh", "Fateme", "Monire"]
    surnames = ["Arbanshirani", "Shamsi", "AliAkbarian", "Vatankhah", "Razavi",
                "Akbari", "Ahmadi", "Mohagheghian", "Nouri", "Esnaashari",
                "Mahdinia", "Noroozi", "Hajikarami", "Mirsadegh"]
    return "".join([random.choice(names), random.choice(surnames)])

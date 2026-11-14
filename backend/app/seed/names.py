"""Synthetic names and work emails, regional to each country. No real people."""

import random
from collections.abc import Iterable

_REGION_BY_COUNTRY = {
    "US": "anglo",
    "GB": "anglo",
    "CA": "anglo",
    "AU": "anglo",
    "IN": "indian",
    "DE": "german",
    "BR": "brazilian",
    "SG": "singaporean",
}


def _names(comma_separated: str) -> tuple[str, ...]:
    return tuple(name.strip() for name in comma_separated.split(","))


_FIRST_NAMES = {
    "anglo": _names(
        "James, Olivia, Liam, Emma, Noah, Ava, Ethan, Sophia, Mason, Isla, Lucas, Mia, "
        "Jack, Grace, Henry, Chloe, Oliver, Emily, Leo, Hannah"
    ),
    "indian": _names(
        "Ravi, Ananya, Arjun, Divya, Karthik, Neha, Priya, Rahul, Sneha, Vikram, Aditya, "
        "Pooja, Rohan, Kavya, Siddharth, Meera, Aarav, Isha, Nikhil, Lakshmi"
    ),
    "german": _names(
        "Jonas, Lena, Felix, Anna, Lukas, Marie, Paul, Sophie, Maximilian, Laura, Leon, "
        "Julia, Finn, Hannah, Elias, Clara, Moritz, Lea, Tobias, Katrin"
    ),
    "brazilian": _names(
        "Lucas, Sofia, Gabriel, Julia, Mateus, Ana, Pedro, Beatriz, Rafael, Larissa, "
        "Thiago, Camila, Bruno, Mariana, Felipe, Isabela, Diego, Fernanda, Gustavo, "
        "Leticia"
    ),
    "singaporean": _names(
        "Wei Ling, Jun Hao, Hui Min, Zhi Wei, Siti, Aisha, Rajesh, Mei Ling, Daniel, "
        "Hafiz, Xin Yi, Kai Wen, Nurul, Ryan, Shu Fen, Imran, Jia Hui, Marcus, Farah, "
        "Wen Jie"
    ),
}

_LAST_NAMES = {
    "anglo": _names(
        "Smith, Johnson, Brown, Taylor, Wilson, Clarke, Walker, Wright, Hughes, Edwards, "
        "Brooks, Turner, Parker, Collins, Evans, Chen, Patel, Murphy, Bennett, Reid"
    ),
    "indian": _names(
        "Kumar, Sharma, Mehta, Menon, Reddy, Gupta, Nair, Das, Patil, Singh, Iyer, Rao, "
        "Joshi, Bose, Kapoor, Pillai, Verma, Chatterjee, Desai, Agarwal"
    ),
    "german": _names(
        "Weber, Muller, Schmidt, Schneider, Fischer, Braun, Wagner, Becker, Hoffmann, "
        "Schulz, Koch, Richter, Klein, Wolf, Neumann, Krause, Lange, Hartmann, Werner, "
        "Zimmermann"
    ),
    "brazilian": _names(
        "Silva, Santos, Oliveira, Souza, Martins, Lima, Costa, Pereira, Almeida, Ferreira, "
        "Rodrigues, Gomes, Ribeiro, Carvalho, Rocha, Barbosa, Araujo, Melo, Cardoso, "
        "Teixeira"
    ),
    "singaporean": _names(
        "Tan, Lim, Lee, Ng, Wong, Goh, Chua, Ong, Koh, Teo, Rahman, Abdullah, Kumar, Nair, "
        "Yeo, Chan, Low, Sim, Ismail, Ho"
    ),
}

EMAIL_DOMAIN = "acme.example"


class NameBook:
    """Draws names for a country and hands out unique work emails."""

    def __init__(self, rng: random.Random, reserved: Iterable[str] = ()) -> None:
        self._rng = rng
        self._reserved_names = set(reserved)
        self._used_emails: set[str] = set()

    def person(self, country_code: str) -> tuple[str, str]:
        region = _REGION_BY_COUNTRY[country_code]
        while True:
            first = self._rng.choice(_FIRST_NAMES[region])
            last = self._rng.choice(_LAST_NAMES[region])
            if f"{first} {last}" not in self._reserved_names:
                return f"{first} {last}", self.reserve_email(first, last)

    def reserve_email(self, first: str, last: str) -> str:
        local = f"{first}.{last}".lower().replace(" ", "")
        email, suffix = f"{local}@{EMAIL_DOMAIN}", 1
        while email in self._used_emails:
            suffix += 1
            email = f"{local}{suffix}@{EMAIL_DOMAIN}"
        self._used_emails.add(email)
        return email

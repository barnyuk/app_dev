"""Data transfer object for protocol generation."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from src.generators.docx_generator import generate_protocols

OPERATOR_INFO = {
    'BEST': {
        'name': 'Закрытое акционерное общество «Белорусская сеть телекоммуникаций», 220030, Республика Беларусь, г. Минск, ул. Красноармейская, д. 24.',
        'worker': 'ведущий инженер ОАДО ЗАО «БеСТ» Тигин В.В.'},
    'BE_CLOUD': {
        'name': 'ООО «Белорусские облачные технологии», 220004, г. Минск, ул. Клары. Цеткин, 24, пом. 602.',
        'worker': 'руководитель группы ТУ УИиПОСПЭ Малаховская М.А.'},
    'A1': {
        'name': 'Унитарное предприятие «А1», 220030, Республика Беларусь, г. Минск, ул. Интернациональная, 36-2.',
        'worker': 'руководитель группы по работе с ЦГ Пархутич А.И.'}
}


@dataclass
class ProtocolInfo:
    operator: str
    bsn_id: str
    bsn_address: str
    standarts: list
    permissions: dict
    protocol_number: int = 1
    date: str = field(
        default_factory=lambda: (datetime.now() + timedelta(hours=24)).strftime('%d.%m.%Y'))
    word_date: str = field(
        default_factory=lambda: (datetime.now() + timedelta(hours=48)).strftime('%d.%m.%Y'))
    city_minsk: bool = False
    sitplan_dir: str = None
    output_dir: str = None

    def __post_init__(self):
        self.operator_worker: str = OPERATOR_INFO[self.operator]['worker']
        self.operator_address: str = OPERATOR_INFO[self.operator]['name']
        self.frequences = sorted({int(key) for key in self.permissions})
        azimuths = {int(az) for values in self.permissions.values() for az in values}
        self.azimuthes = [str(az) for az in sorted(azimuths)]

    def show_frequences(self) -> str:
        """Return frequencies as a human-readable string, e.g. '1, 2 и 3'."""
        if len(self.frequences) == 1:
            return str(self.frequences[0])
        return ', '.join(map(str, self.frequences[:-1])) + ' и ' + str(self.frequences[-1])

    def show_standarts(self):
        if len(self.standarts) == 1:
            return str(self.standarts[0])
        return ', '.join(map(str, self.standarts[:-1])) + ' и ' + str(self.standarts[-1])


    def work(self) -> None:
        generate_protocols(self, sitplan_dir=self.sitplan_dir, output_dir=self.output_dir)

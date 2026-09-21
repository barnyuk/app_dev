"""Merge data from multiple sources and generate protocol documents."""

import logging

from src.data_sources.parser_rep import get_data_from_maps
from src.dto.protocol_dto import ProtocolInfo
from src.generators.excel import make_excel

logger = logging.getLogger(__name__)


def process_job(operator: str, bsn_id: str, token: str,
                protocol_number: int = 1,
                sitplan_dir=None, output_dir=None,
                date: str = None, word_date: str = None) -> ProtocolInfo:
    """Fetch data for a single base station and generate its protocols."""

    parse_info, is_minsk = get_data_from_maps(operator, bsn_id, token=token)

    kwargs = dict(
        bsn_id=bsn_id,
        operator=operator,
        bsn_address=parse_info['address'],
        standarts=parse_info['standarts'],
        permissions=parse_info['freq'],
        city_minsk=is_minsk,
        protocol_number=protocol_number,
        sitplan_dir=sitplan_dir,
        output_dir=output_dir,
    )
    if date:
        kwargs['date'] = date
    if word_date:
        kwargs['word_date'] = word_date

    protocol_info = ProtocolInfo(**kwargs)
    protocol_info.work()
    return protocol_info


#def process_jobs(jobs: list, token: str,
#                 sitplan_dir=None, output_dir=None) -> None:
#    """Process a list of (operator, bsn_id) jobs, logging errors per job."""
 #   for operator, bsn_id in jobs:
  #      try:
   #         print('kek')
    #        process_job(operator, bsn_id, token,
     #                   sitplan_dir=sitplan_dir, output_dir=output_dir)
      #      make_excel(ProtocolInfo.isinstances)            
       # except Exception as e:
        #    logger.error('Ошибка обработки %s / БС %s: %s', operator, bsn_id, e)


#def concatenate_lists(A1: list, best: list, be_cloud: list, token: str,
 #                     sitplan_dir=None, output_dir=None) -> None:
  #  """Build a combined job list from operator-specific BS lists and process it."""
   # jobs = (
    #    [('A1', str(bsn_id)) for bsn_id in set(A1)]
     #   + [('BEST', str(bsn_id)) for bsn_id in set(best)]
      #  + [('BE_CLOUD', str(bsn_id)) for bsn_id in set(be_cloud)]
    #)

    #if not jobs:
     #   raise ValueError('списки БС пусты')

    #process_jobs(jobs, token, sitplan_dir=sitplan_dir, output_dir=output_dir)

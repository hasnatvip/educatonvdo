from typing import Optional

METADATA =\
{
	'name': 'EducationVdo',
	'description': 'Industry leading face manipulation platform',
	'version': '3.9.1',
	'license': 'OpenRAIL-AS',
	'author': 'Henry Ruhs',
	'url': 'https://educationvdo.io'
}


def get(key : str) -> Optional[str]:
	return METADATA.get(key)

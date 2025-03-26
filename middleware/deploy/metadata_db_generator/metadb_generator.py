
# pylint: disable=deprecated-module
# pylint: disable=import-outside-toplevel
import sys
from argparse import ArgumentParser
from distutils.util import strtobool

from middleware.deploy.metadata_db_generator.db_instance_generator import DBInstance
from middleware.deploy.metadata_db_generator.ddl_generator import DDLGenerator
from middleware.deploy.metadata_db_generator.dml_generator import DMLGenerator


def _parse_args(sys_argv):
    parser = ArgumentParser()
    parser.add_argument('-rd', '--recreate_database', required=False, default="false",
                        help='Flag indicate if either recreate metadb or not',
                        type=strtobool)
    parser.add_argument('-psf', '--project_settings_file', required=True,
                        help='Path to project settings file')
    parser.add_argument('-env', '--environment', required=True,
                        help='Environment name')
    parser.add_argument('-ws', '--workspace', required=True,
                        help='Path to your workspace')
    parser.add_argument('-fwv', '--framework_version', required=True,
                        help='Framework version')
    parser.add_argument('-reg', '--region', required=True,
                        help="AWS region")
    args, _ = parser.parse_known_args(sys_argv)
    return args


def _main(sys_argv):
    import logging
    logging.basicConfig()
    logging.getLogger('sqlalchemy').setLevel(logging.DEBUG)

    args = _parse_args(sys_argv)
    DBInstance(args).generate()
    DDLGenerator(args).generate()
    DMLGenerator(args).generate()


if __name__ == '__main__':
    _main(sys.argv)

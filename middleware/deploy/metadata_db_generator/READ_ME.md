### MetaDB Generator

Generator created for creation of Metadatabase.
What the generator is doing in more detail:
1. It will create new DB instance if it does not exists. During creation it generate the password which is automatically saved into Secret manager with name passed from input arguments
2. Create all tables. You can also recreate DB from scratch using input argument _recreate_database_
3. Insert all metadata as permission types, connection types,...

### Input arguments

Each generator has the following common input arguments:

| Argument name (short name/long name) | Type    | Mandatory | Default value          | Description                                      | 
|--------------------------------------|---------|-----------|------------------------|--------------------------------------------------|
| -rd/--recreate_database              | bool    | No        | N/A                    | Flag indicate if either recreate metadb or notr |
| -psf/--project_settings_file         | string  | Yes       | N/A                    | Path to project settings file |
| -env/--environment                   | string  | Yes       | N/A                    | Environment |
| -ws/--workspace                      | string  | Yes       | N/A                    | Path to your workspace |
| -fwv/--framework_version             | string  | Yes       | N/A                    | Framework version |

    
### Configuration

As a input is a project setting file, section metadatabase. More info you can see [here](https://share.merck.com/display/ADI/DIFW+version+2+-+Getting+Started)
    

### How to run generator

Template:

```bash
python3 \
    <path_to_fw_repository>/deploy/generators/metadata_db/metadb_generator.py \
    -recreate_database <recreate_database> \
    -project_settings_file <project_settings_file> \
    -env <environment> \
    -workspace <workspace> \
    -framework_version <framework_version> 
```

Sample:

```bash
python3 \
    <path_to_fw_repository>/deploy/generators/metadata_db/metadb_generator.py \
    -recreate_database true \
    -project_settings_file project_settings\glue_framework_project_settings_bck.json \
    -env dev\
    -workspace C:\GITMSD\nextgen-etl-pipeline \
    -framework_version 2.2.0-SNAPSHOT \
    -db_credentials_secret_manager data-ingest-difw-metadb-ui-credentials \
```
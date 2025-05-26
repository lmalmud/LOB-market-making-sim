TO CONFIGURE VIRTUAL ENVIRONMENT
poetry install                   
poetry run python -m ipykernel install \
    --user --name approxlob-env \
    --display-name "Poetry (approxlob)"

TO RUN:
poetry run python <filename>
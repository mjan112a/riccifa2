import streamlit.web.bootstrap as bootstrap
from streamlit.web.server import Server

def run():
    bootstrap.run(
        file=__file__,
        command_line="streamlit run app.py",
        args=[],
        flag_options={},
    )

if __name__ == "__main__":
    run()
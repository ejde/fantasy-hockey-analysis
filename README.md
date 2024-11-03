# Fantrax Fantasy Hockey Analysis - Streamlit Application

Welcome to the **Fantrax Fantasy Hockey Analysis** app! This application leverages **Google Gemini AI**, **LangChain**, and a forked version of **Fantrax API** to help you manage your fantasy hockey team effectively. You can view your current roster, available players, and receive AI-powered recommendations for improving your team's standing in the league. Built to play around with fantasy hockey data and LLM-tech.

## Features

- **Login and Session Management**: Authenticate with your Fantrax account to access private league information.
- **Team Selection**: Easily select a team from your league and view the roster.
- **AI-Powered Recommendations**: Google Gemini provides personalized recommendations to enhance your team's standing.

## How to Run the Application Locally

### Prerequisites

1. **Python 3.8+** is required.
2. **Streamlit**, **Fantrax API**, **LangChain**, **Google Generative AI**, and other dependencies need to be installed.

### Installation Steps

1. **Clone the Repository**

   ```sh
   git clone https://github.com/yourusername/fantasy-hockey-manager.git
   cd fantasy-hockey-manager
   ```

2. **Install Dependencies**
   Use `pip` to install the required Python packages.

   ```sh
   pip install -r requirements.txt
   ```

3. **Set Up Optional Secret Environment Variables**
   - **Google API Key**: Obtain an API key for Google Gemini and store it in the `./streamlit/secrets.toml` file with the key `gemini_key`. Used in concert with `league_whitelist`, will bypass entering the API key on every render.
   - **League Whitelist**: List of league ids where we want to use the `gemini_key` above to skip entering the API key on every render.
   - **Default Stats**: For rotisserie based leagues, you can establish a default stat to display in the `default_stat` variable in `secrets.toml`

4. **Run the Application**
   Start the Streamlit application.

   ```sh
   streamlit run app.py
   ```

### File Structure

- **appy.py**: Main entry point for the Streamlit application, which initializes the session, shows the league standings and AI-powered recommendations.
- **utils.py**: Helper functions for transforming data to a usable format.
- **requirements.txt**: Lists the required packages for running the app.

## Usage

1. **Login**: Use your Fantrax credentials to log in.
2. **Select a Team**: Choose your team from the dropdown list.
4. **Generate Recommendations**: View AI-powered suggestions for player acquisitions, drops, or trades to improve your standings.

## Technologies Used

- **Streamlit**: Web framework for building the UI of the app.
- **Fantrax API**: A forked version to fetch data such as roster, available players, and standings.
- **LangChain & Google Generative AI (Gemini)**: To interact with Google Gemini for generating strategic recommendations.

## Future Improvements

- **Find players**: Search for available players based on recommendations, and generate specific claims or drops from the team. Will likely experiment with langchain, an agent framework or the assistants API from OpenAI.
- **Advanced Visualization**: Add more charts and visual aids to show changes in team performance after applying recommendations.
- **User Preferences**: Allow customization of AI recommendation settings, such as risk tolerance or positional needs.

## Troubleshooting

- **Cannot Connect to Google Gemini**: Check your API key and ensure it is correctly set in the environment variables.
- **Button Actions Not Reflecting**: Sometimes buttons may need to use `st.experimental_set_query_params()` for proper reruns.

## Contributions

Feel free to fork this repository, submit pull requests, or suggest features. Any contributions to improve the functionality or expand the app are welcome.

## License

This project is licensed under the MIT License.

## Contact

For questions or support, please reach out at [ejdevangelista@gmail.com].

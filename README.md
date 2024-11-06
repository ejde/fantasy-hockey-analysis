# Fantrax Fantasy Hockey Analysis - Streamlit Application

Welcome to the **Fantrax Fantasy Hockey Analysis** app! This application leverages **Google Gemini AI**, **LangChain**, and a forked version of **Fantrax API** to help you manage your fantasy hockey team effectively. You can view your current roster, available players, and receive AI-powered recommendations for improving your team's standing in the league. Built to play around with fantasy hockey data and LLM-tech with my family's fantasy hockey league data. And to find a way to win! Available at [Streamlit Community Cloud](https://fantasy-hockey-llm.streamlit.app/) For those without a Fantrax League, you can see a short video demo here.

https://github.com/user-attachments/assets/81570088-64d6-4bff-b349-acf3593be1df

## Features

- **Login and Session Management**: Authenticate with your Fantrax account to access private league information.
- **AI-Powered Recommendations**: Google Gemini provides personalized recommendations to enhance your team's standing.
- **Chat with your Team**: Chat with the team, where user is the GM and the chatbot acts as the head coach.

## How to Run the Application Locally

### Prerequisites

1. **Python 3.8+** is required.
2. **Streamlit**, **Fantrax API**, **LangChain**, **Google Generative AI**, and other dependencies need to be installed.

### Installation Steps

1. **Clone the Repository**

   ```sh
   git clone https://github.com/yourusername/fantasy-hockey-analysis.git
   cd fantasy-hockey-analysis
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
   streamlit run Home.py
   ```

### File Structure

- **Home.py**: Main entry point for the Streamlit application, which initializes the session, shows the league standings and AI-powered recommendations.
- **Chat_With_Yer_Team.py**: Chatbot functionality
- **utils.py**: Helper functions for transforming data to a usable format.
- **requirements.txt**: Lists the required packages for running the app.

## Usage

1. **Login**: Use your Fantrax credentials to log in on the Home page
2. **Chat with your team**: Chat with the team, where the user is the GM and the chatbot acts as the head coach.

## Technologies Used

- **Streamlit**: Web framework for building the UI of the app.
- **Fantrax API**: A forked version supporting rotisserie based leagues, to fetch data such as roster, available players, and standings. Will try to get these into upstream master at some point.
- **LangChain & Google Generative AI (Gemini)**: To interact with Google Gemini for generating strategic recommendations.

## Future Improvements

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

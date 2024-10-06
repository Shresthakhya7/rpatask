from robocorp.tasks import task
from RPA.Browser.Selenium import Selenium
from RPA.Excel.Files import Files
import time
import psycopg2

class Rottentomatoes:
    def __init__(self):
        self.browser=Selenium()
        self.rottentomato_url="https://www.rottentomatoes.com/"
        self.browser.open_chrome_browser(self.rottentomato_url)
        self.browser.maximize_browser_window()

    def read_movie_list_from_excel(self):
        excel = Files()
        excel.open_workbook("Movies.xlsx")
        movie_list=excel.read_worksheet_as_table(header=True)
        excel.close_workbook()
    
        return [movie['Movie'] for movie in movie_list]
    
    def search_movie(self,movie_name):
        url = self.rottentomato_url + f'search?search={movie_name}'
        self.browser.go_to(url)
        time.sleep(1)

    # def scroll_to_load_movies(self):
    #     for _ in range(2):
    #         self.browser.press_keys(None, 'PAGE_DOWN')
    #         time.sleep(1)
        
    #     for _ in range(2):
    #         self.browser.press_keys(None, "PAGE_UP")
    #         time.sleep(1)

    
    def exact_movie_details(self, movie_name):
        movie_tab_xpath="//*[@id='search-results']/nav/ul/li[2]/span"

        try:
            # Wait for the Movies tab to be visible and click it
            if self.browser.is_element_visible(movie_tab_xpath):
                self.browser.click_element(movie_tab_xpath)
                time.sleep(1)  # Wait for the movies section to load
            else:
                print(f"'Movies' tab not found for: {movie_name}")
                self.insert_movie_data(movie_name, None, None, None, None, None, [], status='NO movies section found')
                return
        except Exception as e:
            print(f"Error clicking on 'Movies' tab: {e}")
            return
        
        movie_results_xpath="//*[@id='search-results']/search-page-result/ul/search-page-media-row/a[2]"
        # movie_years_xpath="//*[@id='search-results']/search-page-result[1]/ul/search-page-media-row[1]//li/div[3]/span[1]"
        # movie_years=self.browser.get_webelements(movie_years_xpath)
        
        try:
            movie_results=self.browser.get_webelements(movie_results_xpath)
            exact_matches=[]

            for movie in movie_results:
                movie_title=self.browser.get_text(movie)
                if movie_name.lower() == movie_title.lower():
                    exact_matches.append(movie)

            if not exact_matches:
                print(f"No movies found: {movie_name}")
                self.insert_movie_data(movie_name, None, None, None, None, None, [], status='NO exact match found')
                return

            most_recent_movie = exact_matches[0]
            movie_url = most_recent_movie.get_attribute('href')
            # self.browser.wait_until_element_is_visible(movie_results)
            # self.scroll_to_load_movies()
            # Extract details from the selected movie page
            self.browser.go_to(movie_url)
            time.sleep(1) 

        except Exception as e:
            print(f"Error during movie selection: {e}")
            return

        # Proceed with extracting additional movie details
        self.extract_movie_details(movie_name, movie_url)

    def extract_movie_details(self,movie_name, movie_url):
        tomatometer_score_xpath="//*[@id='modules-wrap']/div[1]/media-scorecard/rt-button[2]/rt-text"
        popcornmeter_score_xpath="//*[@id='modules-wrap']/div[1]/media-scorecard/rt-button[5]/rt-text"
        storyline_xpath="//*[@id='modules-wrap']/div[1]/media-scorecard/div[1]/drawer-more/rt-text"
        rating_xpath="//*[@id='modules-wrap']/div[1]/media-scorecard/rt-link[2]"
        genres_xpath="//*[@id='main-page-content']/div/aside/section/div[1]/ul/li[2]"
        
        try:
            tomatometer_score=self.browser.get_text(tomatometer_score_xpath)
            tomatometer_score=tomatometer_score.replace('%','')
            popcornmeter_score=self.browser.get_text(popcornmeter_score_xpath)
            popcornmeter_score=popcornmeter_score.replace('%','')
            storyline=self.browser.get_text(storyline_xpath)
            rating=self.browser.get_text(rating_xpath)
            

            # self.scroll_to_load_movies()

            print(f"Movie:{movie_name}")
            print(f"Tomatometer Score:{tomatometer_score}")
            print(f"Popcornmeter Score:{popcornmeter_score}")
            print(f"Storyline:{storyline}")
            print(f"Rating:{rating}")

            reviews=self.extract_reviews(movie_url)
            genres = self.browser.get_text(genres_xpath)
            genres = [genre.strip() for genre in genres.split(',')]
            genres = '/'.join(genres)
            
            print(f"genres:{genres}")

            self.insert_movie_data(
                movie_name, 
                tomatometer_score, 
                popcornmeter_score, 
                storyline, 
                rating, 
                genres, 
                reviews
            )
            if reviews:
                print(f"Top 5 Reviews for {movie_name}: {reviews}")
            else:
                print(f"No reviews found for {movie_name}")
        except Exception as e:
            print(f"Error while extracting details for '{movie_name}': {e}")
    

    def extract_reviews(self,movie_url):
        # formatted_movie_name = movie_name.replace(' ', '_').lower()
        critics_review_xpath="//*[@id='reviews']/div/div/div[2]/p[1]"

        try:
            # view_all_reviews_url = self.rottentomato_url + f'm/{formatted_movie_name}/reviews'
            view_all_reviews_url = movie_url + '/reviews?type=top_critics'
            self.browser.go_to(view_all_reviews_url)
            time.sleep(1)

            # Find the review elements
            review_elements = self.browser.get_webelements(critics_review_xpath)

            # Extract the text of the top 5 reviews
            top_reviews = [review.text.strip() for review in review_elements[:5]]

            print("Top 5 Reviews:\n")
            for index, review in enumerate(top_reviews, 1):
                print(f"Review {index}: {review}\n")

            return top_reviews

        except Exception as e:
            print(f"Error while extracting reviews: {e}")
            return []



    ##Database Connection
    def connect_database(self):
        """Establish a connection to the PostgreSQL database."""
        # PostgreSQL connection details
        db_host = 'localhost'
        db_name = 'movie_db'
        db_user = 'postgres'
        db_password = 'hello'

        try:
            # Connect to PostgreSQL database
            self.connection = psycopg2.connect(
                host=db_host,
                database=db_name,
                user=db_user,
                password=db_password
            )
            print("Database connection established.")
            self.cursor = self.connection.cursor()
            self.create_table()
        except psycopg2.Error as e:
            print(f"Database connection error: {e}")
            self.connection = None
    
    def create_table(self):
        """Create the movies table if it doesn't exist."""
        if self.connection:
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS movies (
                    id SERIAL PRIMARY KEY,
                    movie_name VARCHAR(255),
                    tomatometer INTEGER,
                    popcornmeter INTEGER,
                    storyline TEXT,
                    rating VARCHAR(50),
                    genres VARCHAR(255),
                    review_1 TEXT,
                    review_2 TEXT,
                    review_3 TEXT,
                    review_4 TEXT,
                    review_5 TEXT,
                    status VARCHAR(50) NOT NULL
                )
                """
            )
            self.connection.commit()
        else:
            print("No connection available to create the table.")

    
    def insert_movie_data(self, movie_name, tomatometer_score, popcornmeter_score, storyline, rating, genres, reviews, status='Success'):
        """Insert movie data into the database."""
        if self.connection:
            try:
                # Prepare the SQL statement
                insert_query = """
                INSERT INTO movies (
                    movie_name,tomatometer,popcornmeter, storyline, rating, genres, review_1, review_2, review_3, review_4, review_5, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                # Prepare the data to be inserted
                review_data = [reviews[i] if i < len(reviews) else None for i in range(5)]
                review_data = (movie_name, tomatometer_score, popcornmeter_score, storyline, rating, genres) + tuple(review_data) + (status,)

                # Execute the insert query
                self.cursor.execute(insert_query, review_data)
                self.connection.commit()
                print(f"Data inserted for movie: {movie_name} with status: {status}")
            except psycopg2.Error as e:
                print(f"Error inserting data for '{movie_name}': {e}")
        else:
            print("No database connection available.")
        
@task
def __init__main():
    obj = Rottentomatoes()
    obj.connect_database()
    movie_list = obj.read_movie_list_from_excel()
    for movie in movie_list:
        obj.search_movie(movie)
        obj.exact_movie_details(movie)


        
    
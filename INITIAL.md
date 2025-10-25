## FEATURE:

Laughter Detector and Counter, from Limitless AI ambient microphone.  
-After a simmple yet secure authentication over https (email/password rather than magic link probably), securely allow logged-in user to input their limitless pendant API key, in a VERY DEAD simple mobile responsive webpage.
--ensure all limitless keys are encrypted in transit and at rest
--there should be a way to completely wipe a limitless key from record if user requests

-on a nightly basis, extract audio segments through the limitless api from the 24 hour period before the current day, and the audio segments from the current day up to the current time in the users time zone. 
--If the pevious day has already been retrieved, do not retrieve it again. if the current day has already been retrieved, only retrieve audio after the latest timestamp of audio retrieved (presumably securly stored in a database - maybe supabase, because we can use their authentication)
--there may be limits (maybe 60 or 120) of minutes that audio can be retrieved from the limitless api

-run the tensorflow model YAMNet on the audio segments to idnetify the number of laughs detected over each day that was retrieved. save the timestamps of the detected laughter, and probability % of each detection. Minimize the amount of file conversaions necessarry to get the audio in the correct format between what is extracted from limitless and inputted into yamnet.

-extract an audio clip for each of the segments detected, configurable to about 2 seconds before and after the timestamp identified by YAMNet

-DELETE the original audio downloaded from limitless after the clips have been saved, securely. If the clips have not been saved, or there is another reason there are orphaned audio snippets, have a cleanup function periodically remove orphaned audio so there is no unaccounted for persistent storage of audio.

-when the user logs in - in the DEAD simple mobile responsive design, show one card for each complete day of audio analysed, with a bright background each day, and a large number indicating the number of laughs detected on that day, with the Day of the week listed underneath. Show an appropriate status if no audio has been found, or there's an error with the limitless key, or whatever status is crisply informative to the user if they dont see the expected daily cards.
--if the user taps/clicks on the day of the week in any given card, they are shown a view of that day with a clean simple table with 4 columns. each row repeesents the segment of laughter detected in chronological order from earliest to latest. the first column has the audio clip which the user can click play to hear, with a timestamp below, the second column has a percentage probability that the yamnet model output, and the third column is a notes field that the user can add a free text comment to. the fourth column has a delete button which will delete that audio segment and reduce the count of laughs for that day. the 2nd column has a filter button to use a threshold to only show laughter segments above a certain % in the table. this is only for filtering the table view and does not impact the number of laughs detected for that day saved in the database and displayed in the main card.
--the user should have the option a the bottom of any given day veiw to delete all the audio from that day.

--below all the audio cards on the main view there should be two buttons, one to delete all audio clips from all days, and two to delete the limitless key from any storage and from the system. if the delete limitless key is clicked and user confirms, then the data from all days should be deleted and the limitless key removed from storage and the screen resets to the orignial authenticataed form where a input field is presented to accept a limitless key

## EXAMPLES:

In examples/ folder there is a sample giggles.py file where i've successfully got limitless data downloaded for a fixed date range, and yamnet to run inference on CPU. giggles_eval.py is a file that creates a sample view of the table with the snipped audio clip for the user to play. "Screenshot 2025-10-23 at 5.40.14 PM.png" is a sample of what a date card can look like - it is a screenshot from the nike run club. note the bottom menu is not needed and the text between cards is unnecessary. the "Half Marathon" text is where the date should go.

## DOCUMENTATION:

Limitless API documentation: https://www.limitless.ai/developers
YAMNet documentation: https://www.tensorflow.org/hub/tutorials/yamnet


## OTHER CONSIDERATIONS:

This project needs to be developed with security as the top unambiguous requirement. To start only about 2-5 users will be using the site, so it cannot be run on my local computer. I will need to host securly on a virtual private server like digitalocean, securely gated with something like cloudflaire zero-trust/tunnel, and authenticated securely with something like supabase. supabase can probably be used as the database if it is used for authentication of the user. MFA is probably a good idea. I am open to other setups and security stacks if there is reason to believe that it offers better security for the limitless key and audio data.
Do not overengineer or overcomplicate this in any way beyond absolute necessary. The UI should be dead simple and function on any mobile smart device with minimized complications for maximum compatibility and minimum state management complexity.
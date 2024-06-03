import json
import requests
import random
from urllib.parse import urljoin
from loguru import logger
from typing import Any, Dict, Optional, Union


class LoginError(Exception):
    """Custom exception for login failures."""

    pass


class PokeRogueAPI:
    """
    API client for interacting with the PokeRogue service.

    Source: https://github.com/pagefaultgames/pokerogue/blob/12bd22f2ca2204af125a4faab985c4d2b9017aea/src/utils.ts#L265
    """

    BASE_URL = "https://api.pokerogue.net"

    def __init__(
        self,
        username: str,
        password: str,
        is_local: bool = False,
        server_url: str = "http://localhost:8000",
    ):
        """
        Initializes the PokeRogueAPI client.

        Args:
            username (str): The username for authentication.
            password (str): The password for authentication.
            is_local (bool, optional): Whether to use a local server URL. Defaults to False.
            server_url (str, optional): The URL of the local server. Defaults to "http://localhost:8000".
        """
        self.api_url = server_url if is_local else self.BASE_URL
        self.session = requests.Session()
        self.username = username
        self.password = password
        self.headers = self.generate_random_headers()

        self._secret_id: Optional[str] = None
        self._trainer_id: Optional[str] = None

        self._login()

    def get(
        self, endpoint: str, params: Dict[str, Any] = {"datatype": 0}
    ) -> requests.Response:
        """
        Sends a GET request to the specified endpoint.

        Args:
            endpoint (str): The API endpoint to send the request to.
            params (Dict[str, Any], optional): The query parameters for the request. Defaults to {"datatype": 0}.

        Returns:
            requests.Response: The response from the API.
        """
        return self._request("get", endpoint, params=params)

    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        params: Dict[str, Any] = {"datatype": 0},
    ) -> requests.Response:
        """
        Sends a POST request to the specified endpoint.

        Args:
            endpoint (str): The API endpoint to send the request to.
            data (Optional[Dict[str, Any]], optional): The form data to send in the request. Defaults to None.
            json (Optional[Dict[str, Any]], optional): The JSON data to send in the request. Defaults to None.
            params (Dict[str, Any], optional): The query parameters for the request. Defaults to {"datatype": 0}.

        Returns:
            requests.Response: The response from the API.
        """
        return self._request("post", endpoint, data, json, params)

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        params: Dict[str, Any] = {"datatype": 0},
    ) -> requests.Response:
        """
        Sends a request to the specified endpoint using the specified method.

        Args:
            method (str): The HTTP method to use (e.g., "get", "post").
            endpoint (str): The API endpoint to send the request to.
            data (Optional[Dict[str, Any]], optional): The form data to send in the request. Defaults to None.
            json (Optional[Dict[str, Any]], optional): The JSON data to send in the request. Defaults to None.
            params (Dict[str, Any], optional): The query parameters for the request. Defaults to {"datatype": 0}.

        Returns:
            requests.Response: The response from the API.
        """
        url = urljoin(self.api_url, endpoint)
        response = self.session.request(
            method,
            url,
            params=params,
            data=data if method != "get" else None,
            json=json if method != "get" else None,
            headers=self.headers,
        )
        response.raise_for_status()
        return response

    def set_headers(self, headers: Dict[str, str]) -> None:
        """
        Sets the headers for the session.

        Args:
            headers (Dict[str, str]): The headers to set for the session.
        """
        self.session.headers.update(headers)

    def generate_random_headers(self) -> Dict[str, str]:
        """
        Generates random headers for the session.

        Returns:
            Dict[str, str]: The generated headers.
        """
        chrome_major_versions = list(range(110, 126))
        platforms = [
            "Windows NT 10.0; Win64; x64",
            "Windows NT 6.1; Win64; x64",
            "Macintosh; Intel Mac OS X 10_15_7",
            "Macintosh; Intel Mac OS X 11_2_3",
            "X11; Linux x86_64",
            "X11; Ubuntu; Linux x86_64",
        ]

        random_platform = random.choice(platforms)
        random_chrome_major_version = random.choice(chrome_major_versions)

        headers = {
            "Accept": "application/x-www-form-urlencoded",
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://pokerogue.net/",
            "Sec-Ch-Ua": f'"Google Chrome";v="{random_chrome_major_version}", "Chromium";v="{random_chrome_major_version}", "Not.A/Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": random_platform.split(";")[0],
            "User-Agent": f"Mozilla/5.0 ({random_platform}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random_chrome_major_version}.0.0.0 Safari/537.36",
        }

        return headers

    def _login(self) -> None:
        """
        Logs in to the PokeRogue API and sets the authorization header.

        Source: https://github.com/pagefaultgames/pokerogue/blob/50c1f8aee461a45d8f69de8f02a452a34b59f78b/src/ui/login-form-ui-handler.ts#L64
        """
        try:
            response = self.post(
                "account/login",
                data={"username": self.username, "password": self.password},
            )
            self.headers["authorization"] = response.json()["token"]

        except Exception as e:
            logger.info("Couldn't Login! (Incorrect credentials or server down.)")
            logger.exception(e)
            raise LoginError()

    def get_trainer(self) -> Optional[Dict[str, Any]]:
        """
        Retrieves trainer data from the API.

        Source: https://github.com/pagefaultgames/rogueserver/blob/68caa148f6a965f01ea503d42f56daad6799e5f7/api/common.go#L55

        Returns:
            Optional[Dict[str, Any]]: The trainer data, or None if an error occurs.
        """
        try:
            trainer = self.get("savedata/get").json()
            self._trainer_id = trainer["trainerId"]
            self._secret_id = trainer["secretId"]
            return trainer

        except Exception as e:
            logger.exception(e)
            return None

    def set_trainer(self, trainer: Dict[str, Any]) -> bool:
        """
        Updates trainer data on the API.

        Source: https://github.com/pagefaultgames/rogueserver/blob/68caa148f6a965f01ea503d42f56daad6799e5f7/api/common.go#L56
        https://github.com/pagefaultgames/rogueserver/blob/68caa148f6a965f01ea503d42f56daad6799e5f7/api/endpoints.go#L410

        Args:
            trainer (Dict[str, Any]): The trainer data to update.

        Returns:
            bool: True if the update is successful, False otherwise.
        """
        try:
            return (
                self.post("savedata/update", data=json.dumps(trainer)).status_code
                == 200
            )

        except Exception as e:
            logger.exception(e)
            return False

    def get_slot(self, slot_index: int) -> Optional[Dict[str, Any]]:
        """
        Retrieves data for a specific slot from the API.

        Source: https://github.com/pagefaultgames/rogueserver/blob/68caa148f6a965f01ea503d42f56daad6799e5f7/api/common.go#L55

        Args:
            slot_index (int): The index of the slot to retrieve data for.

        Returns:
            Optional[Dict[str, Any]]: The slot data, or None if an error occurs.
        """
        try:
            return self.get("savedata/get", {"datatype": 1, "slot": slot_index}).json()

        except Exception as e:
            logger.exception(e)
            return None

    def set_slot(self, slot_index: int, data: Dict[str, Any]) -> bool:
        """
        Updates data for a specific slot on the API.

        Source: https://github.com/pagefaultgames/rogueserver/blob/68caa148f6a965f01ea503d42f56daad6799e5f7/api/common.go#L56
        https://github.com/pagefaultgames/rogueserver/blob/68caa148f6a965f01ea503d42f56daad6799e5f7/api/endpoints.go#L410

        Args:
            slot_index (int): The index of the slot to update.
            data (Dict[str, Any]): The data to update for the slot.

        Returns:
            bool: True if the update is successful, False otherwise.
        """
        try:
            if self._trainer_id is None or self._secret_id is None:
                # To update the trainer and secret id.
                self.get_trainer()

            return (
                self.post(
                    "savedata/update",
                    json=data,
                    params={
                        "datatype": 1,
                        "slot": slot_index,
                        "trainerId": self._trainer_id,
                        "secretId": self._secret_id,
                    },
                ).status_code
                == 200
            )

        except Exception as e:
            logger.exception(e)
            return False

    def close(self) -> None:
        """
        Closes the session and clears the instance attributes.
        """
        self.session.close()
        self.session = None
        self._secret_id = None
        self._trainer_id = None
        self.api_url = None
        self.username = None
        self.password = None
        self.headers = None

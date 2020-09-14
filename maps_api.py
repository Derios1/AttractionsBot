import requests

MAP_TOKEN = "ArDNY63QOW78xmYyRUvxCS2uTV0agbQKSiygnc_ubottSt-Jz1xmKXO2KIu5R7Na"
url = "https://dev.virtualearth.net/REST/v1/Routes/DistanceMatrix?"
params = "origins={lat1},{long1}&destinations={lat2},{long2}&travelMode=walking&key={key}"


def get_distance(latitude_1, longitude_1, latitude_2, longitude_2):
    """""""""
    Returns distance in meters
    """""""""
    response = requests.get(url + params.format(lat1=latitude_1,
                            long1=longitude_1,
                            lat2=latitude_2,
                            long2=longitude_2,
                            key=MAP_TOKEN))
    return float(response.json()['resourceSets'][0]['resources'][0]['results'][0]['travelDistance'])*1000


def log_request(logger, body, next):
    logger.debug(body)
    return next()
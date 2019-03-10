;; fare.el -- fare files sharing service for Emacs

;;; Copyright (C) 2019 Viacheslav Chimishuk <vchimishuk@yandex.ru>
;;;
;;; Home page: https://github.com/vchimishuk/fare
;;; Usage: use `fare-show` function to post current buffer or selected region.

(require 'url)

(defvar fare-server "https://files.vchimishuk.pp.ua"
  "Server URL to paste to.")

(defun fare-ok-p (resp-buf)
  "Check if server response is OK"
  (with-current-buffer resp-buf
    (save-excursion
      (goto-char (point-min))
      (re-search-forward "HTTP.*200 OK" nil t))))

(defun fare-header (resp-buf name)
  "Return header value."
  (with-current-buffer resp-buf
    (save-excursion
      (goto-char (point-min))
      (search-forward (concat name ": "))
      (setq s (point))
      (setq e (line-end-position))
      (buffer-substring-no-properties s e))))

(defun fare-show (text)
  "Show user message."
  (with-current-buffer (get-buffer-create "*fare*")
    (read-only-mode -1)
    (erase-buffer)
    (insert text)
    (switch-to-buffer-other-window (current-buffer))
    (special-mode)))

(defun fare-post-text (text)
  "Post text snippet and return URL to newly created file."
  (let ((url-request-method "POST")
        (url-extra-headers '(("Content-Type" . "text/plain")))
        (url-request-data text))
    (url-retrieve fare-server (lambda (status)
                                (if (fare-ok-p (current-buffer))
                                    (fare-show (fare-header (current-buffer)
                                                            "location"))
                                  (switch-to-buffer (current-buffer)))))))

(defun fare-post (&optional arg)
  "Post selected region or buffer."
  (interactive "P")
  (fare-post-text (if (use-region-p)
                      (buffer-substring-no-properties (region-beginning)
                                                      (region-end))
                    (buffer-substring-no-properties (point-min)
                                                    (point-max)))))

(provide 'fare)

require 'erb'
require 'base64'
require 'globby'
require 'open-uri'
require 'octokit'
require 'mail'
require 'yaml'

$config = YAML.load_file('config.yaml') rescue {}

raise "Please configure SendGrid integration" unless $config[:smtp].is_a? Hash
raise "Please go change the SendGrid password now and remove it from the repo" if $config[:smtp].include? :password

$config[:smtp][:password] = ENV['SENDGRID_PASSWORD']
Mail.defaults do
  delivery_method :smtp, $config[:smtp]
end

def sendmail(recipient, subject_line, text, html=nil)
  Mail.deliver do
    to      recipient
    from    $config[:smtp][:from]
    subject subject_line

    text_part do
        body text
    end

    if html
      html_part do
          content_type 'text/html; charset=UTF-8'
          body html
      end
    end
  end
end

def github_client(page_size = 100)
  @token ||= ENV['GITHUB_TOKEN'] || `git config --global github.token`.chomp

  if @token.empty?
    puts "You need to generate a GitHub token:"
    puts "\t * https://help.github.com/en/articles/creating-a-personal-access-token-for-the-command-line"
    puts "\t * git config --global github.token <token>"
    puts
    puts "Export that as the `GITHUB_TOKEN` environment variable or put it in your ~/.gitconfig."
    exit 1
  end

  begin
    client = Octokit::Client.new(:access_token => @token, per_page: page_size)
  rescue => e
    puts "Github login error: #{e.message}"
    exit 1
  end

  client
end

task :default do
  puts 'This automates several github org housekeeping processes.'
  puts
  system("rake -T")
end

desc 'Generate and send a stale PR report with a sample of the oldest open PRs.'
task :stale_pulls do
  org    = $config[:org]
  stale  = github_client.search_issues("is:pr state:open user:#{org} archived:false sort:created-asc")
  sample = stale[:items].sample(15)

  sendmail(
    ENV['EMAIL_ADDRESS'],
    'Housekeeping report: stale pull requests',
    ERB.new(File.read('templates/stale_prs.txt.erb'), nil, '-').result(binding),
    ERB.new(File.read('templates/stale_prs.html.erb'), nil, '-').result(binding),
  )
end

desc 'Check CODEOWNER coverage for all public repositories'
task :codeowner_coverage do
  org    = $config[:org]
  client = github_client
  client.auto_paginate = true

  owners =      client.org_teams(org).map {|team| "@#{org}/#{team[:slug]}" }
  owners.concat client.org_members(org).map {|user| user[:login] }

  missing   = []
  malformed = []
  coverage  = []

  repos = client.repos(org).each do |repo|
    begin
      next if repo[:archived]
      next if repo[:fork]
      next if repo[:private]
      next if repo[:name].start_with? 'puppetlabs-' # modules are following other standards

      sha   = client.commits(repo[:full_name]).first[:sha]
      tree  = client.tree(repo[:full_name], sha, :recursive => true)[:tree]

      files = tree.map {|entry| entry[:path]     if entry[:type] == 'blob' }.compact
      dirs  = tree.map {|entry| entry[:path]+'/' if entry[:type] == 'tree' }.compact  # Globby only matches if directories have the trailing /
      path  = files.find {|f| f =~ /CODEOWNERS/ }
      unless path
        missing << repo
        next
      end

      rules = []
      Base64.decode64(client.contents(repo[:full_name], :path => path).content).split("\n").each do |line|
        rule, owner = line.split
        next unless rule
        next if rule.start_with? '#'

        rules << rule
        malformed << repo unless owners.include? owner
      end

      source = Globby::GlObject.new(files, dirs)
      misses = Globby.reject(rules, source)
      unless misses.empty?
        coverage << repo
      end

    rescue => e
      puts "Borked repo [#{repo[:name]}] #{e.message}"
    end
  end

  sendmail(
    ENV['EMAIL_ADDRESS'],
    'Housekeeping report: CODEOWNERS linting',
    ERB.new(File.read('templates/codeowners.txt.erb'), nil, '-').result(binding),
    ERB.new(File.read('templates/codeowners.html.erb'), nil, '-').result(binding),
  )

end

task :shell do
  require 'pry'
  binding.pry
end

